"""材料模拟：液气流动、挥发与消散、火焰传播、墙体破坏与远域覆写。"""

from __future__ import annotations

import random
from zlib import crc32

from ..i18n import tr
from ..materials import (
    CONTAINER_KINDS,
    SOLID_KINDS,
    GAS_DEFINITIONS,
    LIQUID_DEFINITIONS,
    WALL_DEFINITIONS,
    floor_effect_for,
    plant_burns,
    plant_conducts,
    plant_gas_flow_divisor,
    plant_survives_liquid,
    portent_def,
    floor_fireproof,
    mix_pair,
    OTHER_BY_REACTANT,
    unstable_mix,
    wall_def,
)
from ..materials.reactions import (
    GAS_GAS_PRODUCTS,
    LIQUID_GAS_RECIPES,
    LIQUID_LIQUID_PRODUCTS,
    OTHER_REACTIONS,
    ReactionDef,
)
from ..materials.logic import LOGIC_KINDS

# 棋盘格地板的「常见增益征兆集合」：温和的正面材料征兆（8 回合封顶）。
CHECKER_BUFF_PORTENTS = ("calmed", "warmed", "tear_warm", "moist")
from .entities import Cell, Entity
from ..data.anomalies import ANOMALY_DEFINITIONS
from .gas_kernel import (collect_gas_sources as _kernel_collect_gas_sources,
                         plan_material_transfers as _kernel_plan_transfers)
from ..cy_kernels import enabled as _kernel_enabled
from .constants import (
    ELEV_STEP,
    GAS_DECAY_INTERVAL,
    GAS_MIN_FLOW,
    LIQ_MIN_FLOW,
    LIQUID_ABSORB_INTERVAL,
    LIQUID_DECAY_INTERVAL,
    EXPOSED_ONLY_WALLS,
    Material,
)

# 相变活动格：有相变存量，或仍可熔化的蜡墙。与 phase_changes.WAX 的键保持一致；
# 由材料索引维护，phase_changes.tick 不再每拍全图补扫。
_PHASE_WALL_KINDS = frozenset(('蜡化记忆墙', '烛泪柱'))

# 拨号音环境声源（docs 261022 §13.2／盘点 §2）：浓度门槛、世界回合周期与声径。
# 一个连通气团每周期只在稳定锚点登记一个声源，不让每格每拍各刷一次 AI。
DIAL_TONE_GAS = "拨号音"
DIAL_TONE_MIN_AMOUNT = 12
DIAL_TONE_PERIOD = 4
DIAL_TONE_RADIUS = 3


class _UnstableExplosionResult(tuple):
    """Two-value mix result carrying a local explosion, without shared state."""


class MaterialSimMixin:

    def _emit_combat_fx(self, kind: str, center: tuple[int, int], cells, *,
                        profile=None, motion=None, source=None, path=(), cast_id=None,
                        source_id=None, theme='', projectile_seq=None) -> None:
        """只记录已结算的世界坐标；画面回放不参与伤害或地形计算。"""
        cells = tuple(sorted(set(cells)))
        if not cells:
            return
        self._combat_fx_seq = getattr(self, "_combat_fx_seq", 0) + 1
        events = getattr(self, "_combat_fx_events", [])
        raw = getattr(self, "last_projectile", None) or {}
        event = dict(seq=self._combat_fx_seq, kind=kind, center=tuple(center), cells=cells,
                     action_seq=self.action_seq,
                     projectile_seq=projectile_seq if profile else
                     raw.get("seq") if raw.get("kind") == "throw" or kind == 'spray' else None)
        if profile:
            event.update(profile=profile, motion=motion, source=tuple(source or center),
                         path=tuple(tuple(p) for p in path), cast_id=cast_id,
                         source_id=source_id, theme=theme)
        events.append(event)
        # Keep every event belonging to the newest action, even in large chains.
        self._combat_fx_events = [e for e in events if e.get('action_seq', -1) >= self.action_seq-1]

    @staticmethod
    def _conductive_cell(cell: Cell) -> bool:
        return not cell.solid and (
            cell.liquid >= 8 and cell.liquid_kind in {"水", "导电液态记忆", "稀墨"}
            or cell.aggregate_variant == "金属聚合物"
            # 导电脚线（2026-10-26）：植物也能当介质——它自己不发电，只把一段
            # 断开的导电路接通；能不能被点亮仍由电系求解与实际放电决定。
            or plant_conducts(cell.plant))

    def _conductive_zone(self, origin: tuple[int, int]) -> set[tuple[int, int]]:
        """电场只沿四邻连通介质传播，半径四格且最多二十格。"""
        if not self._conductive_cell(self.cell(*origin)):
            return set()
        zone = {origin}
        queue = [(origin, 0)]
        for (x, y), distance in queue:
            if distance >= 4:
                continue
            for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                if len(zone) >= 20:
                    return zone
                pos = (nx, ny)
                if (pos not in zone and 0 <= nx < self.width and 0 <= ny < self.height
                        and self._conductive_cell(self.cell(nx, ny))):
                    zone.add(pos)
                    queue.append((pos, distance+1))
        return zone

    def _conductive_component(self, origin: tuple[int, int]) -> set[tuple[int, int]]:
        """静电弧：沿四邻导电介质无限延伸，绝缘/断流处自然截断。"""
        if not self._conductive_cell(self.cell(*origin)):
            return set()
        zone = {origin}
        queue = [origin]
        while queue:
            x, y = queue.pop(0)
            for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                pos = (nx, ny)
                if (pos not in zone and 0 <= nx < self.width and 0 <= ny < self.height
                        and self._conductive_cell(self.cell(nx, ny))):
                    zone.add(pos)
                    queue.append(pos)
        return zone

    def _electric_prefix(self) -> str:
        return f"__electric__:{self.depth}:{self.realm_id}:{self.realm_depth}:"

    def _electric_origin_prefix(self) -> str:
        return f"__electric_origin__:{self.depth}:{self.realm_id}:{self.realm_depth}:"

    @staticmethod
    def _electric_origin_entry(key: str, prefix: str):
        body = key[len(prefix):]
        source, sep, coords = body.rpartition("@")
        if not sep:
            return None
        x_text, sep, y_text = coords.partition(":")
        if not sep:
            return None
        try:
            return source, int(x_text), int(y_text)
        except ValueError:
            return None

    @staticmethod
    def _electric_entry(key: str, prefix: str):
        """旧档键 = x:y（无来源）；新键 = source:x:y。"""
        body = key[len(prefix):]
        parts = body.split(":")
        if len(parts) == 2:
            try:
                return "player", int(parts[0]), int(parts[1])
            except ValueError:
                return None
        if len(parts) == 3:
            try:
                return parts[0], int(parts[1]), int(parts[2])
            except ValueError:
                return None
        return None

    def _charge_electric_field(self, cells, *, source: str = "player",
                               origin: tuple[int, int] | None = None,
                               duration: int = 5) -> None:
        # 使用现有的浮点记账字典持久化，不增加存档字段。同来源重新放电替换旧区，
        # 不同来源并存；同格伤害在 tick 时取最大寿命，不重复结算。
        cells = list(cells)
        if not cells:
            return
        origin = tuple(origin) if origin is not None else min(cells)
        prefix = self._electric_prefix()
        origin_prefix = self._electric_origin_prefix()
        start_prefix = f"__electric_start__:{self.depth}:{self.realm_id}:{self.realm_depth}:"
        for key in list(self.player.portent_debt):
            if key.startswith(origin_prefix):
                entry = self._electric_origin_entry(key, origin_prefix)
            elif key.startswith(prefix):
                entry = self._electric_entry(key, prefix)
            elif key.startswith(start_prefix):
                parts = key[len(start_prefix):].split(":", 1)
                entry = (parts[0],) if parts else None
            else:
                continue
            if entry is not None and entry[0] == source:
                self.player.portent_debt.pop(key)
        duration = max(1, int(duration))
        if source in {"player", "battery", "static_arc", "thunder_orb",
                      "arc_bolt", "expansion_e07"}:
            from ..equipment.expansion_runtime import owned_field_duration
            duration = min(6, duration + min(1, owned_field_duration(self)))
        expiry = float(self.time + duration)
        for x, y in cells:
            self.player.portent_debt[f"{prefix}{source}:{x}:{y}"] = expiry
            self.player.portent_debt[
                f"{start_prefix}{source}:{x}:{y}"
            ] = float(self.time)
        self.player.portent_debt[f"{origin_prefix}{source}@{origin[0]}:{origin[1]}"] = expiry

    def electric_field_cells(self, *, at_time: int | None = None) -> set[tuple[int, int]]:
        at_time = self.time if at_time is None else at_time
        prefix = self._electric_prefix()
        best: dict[tuple[int, int], float] = {}
        for key, expiry in list(self.player.portent_debt.items()):
            if not key.startswith(prefix) or expiry < at_time:
                continue
            entry = self._electric_entry(key, prefix)
            if entry is None:
                continue
            _, x, y = entry
            if (0 <= x < self.width and 0 <= y < self.height
                    and self._conductive_cell(self.cell(x, y))):
                best[(x, y)] = max(best.get((x, y), 0.0), float(expiry))
        if not best:
            return set()
        origin_prefix = self._electric_origin_prefix()
        origins = []
        legacy: set[tuple[int, int]] = set()
        for key, expiry in list(self.player.portent_debt.items()):
            if not key.startswith(origin_prefix) or expiry < at_time:
                continue
            entry = self._electric_origin_entry(key, origin_prefix)
            if entry is not None:
                origins.append(entry)
        for key, expiry in list(self.player.portent_debt.items()):
            if not key.startswith(prefix) or expiry < at_time:
                continue
            if key[len(prefix):].count(":") == 1:
                entry = self._electric_entry(key, prefix)
                if entry is not None:
                    legacy.add((entry[1], entry[2]))
        if not origins:
            # 旧档没有来源记录：按旧口径保留全部仍在导电的记账格。
            return set(best)
        # 介质断开后，从仍带电的充能源沿记账格重新取连通区；失去通路的
        # 远端格即使自身还导电、记账未过期，也不再算在电场里。只走已充能
        # 的记账格，不做全图导电扫描（渲染每帧都会读这里）。
        connected: set[tuple[int, int]] = set(legacy) & set(best)
        for _source, x, y in origins:
            origin = (x, y)
            if origin not in best:
                continue
            seen = {origin}
            queue = [origin]
            while queue:
                cx, cy = queue.pop(0)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy),
                               (cx, cy + 1), (cx, cy - 1)):
                    pos = (nx, ny)
                    if pos in seen or pos not in best:
                        continue
                    seen.add(pos)
                    queue.append(pos)
            connected.update(seen)
        return connected

    def _electric_expiry_at(self, x: int, y: int) -> float:
        prefix = self._electric_prefix()
        best = 0.0
        for key, expiry in self.player.portent_debt.items():
            if not key.startswith(prefix):
                continue
            entry = self._electric_entry(key, prefix)
            if entry is not None and entry[1] == x and entry[2] == y:
                best = max(best, float(expiry))
        return best

    def _electric_sources_at(self, x: int, y: int) -> set[str]:
        prefix = self._electric_prefix()
        sources = set()
        for key, expiry in self.player.portent_debt.items():
            if not key.startswith(prefix) or float(expiry) < self.time:
                continue
            entry = self._electric_entry(key, prefix)
            if entry is not None and entry[1:] == (x, y):
                sources.add(entry[0])
        return sources

    def _prune_electric_fields(self) -> None:
        for key in list(self.player.portent_debt):
            if not (key.startswith("__electric__:")
                    or key.startswith("__electric_origin__:")):
                continue
            if float(self.player.portent_debt[key]) < self.time + 1:
                self.player.portent_debt.pop(key, None)
        start_prefix = f"__electric_start__:{self.depth}:{self.realm_id}:{self.realm_depth}:"
        field_prefix = self._electric_prefix()
        for key in list(self.player.portent_debt):
            if not key.startswith(start_prefix):
                continue
            parts = key[len(start_prefix):].split(":", 3)
            if len(parts) != 3:
                self.player.portent_debt.pop(key, None)
                continue
            source, x_text, y_text = parts
            field_key = f"{field_prefix}{source}:{x_text}:{y_text}"
            if field_key not in self.player.portent_debt:
                self.player.portent_debt.pop(key, None)

    def _tick_electric_fields(self, amount: int) -> None:
        cells = self.electric_field_cells(at_time=self.time-amount+1)
        if not cells:
            self._prune_electric_fields()
            return
        affected = []
        for entity in [self.player, *self.enemies]:
            pos = (entity.x, entity.y)
            if entity.integrity <= 0 or pos not in cells:
                continue
            tick_range = range(self.time-amount+1, self.time+1)
            field_prefix = self._electric_prefix()
            start_prefix = f"__electric_start__:{self.depth}:{self.realm_id}:{self.realm_depth}:"
            active_windows = []
            for key, field_expiry in self.player.portent_debt.items():
                if not key.startswith(field_prefix):
                    continue
                entry = self._electric_entry(key, field_prefix)
                if entry is None or entry[1:] != pos:
                    continue
                start_key = f"{start_prefix}{entry[0]}:{entity.x}:{entity.y}"
                start = self.player.portent_debt.get(start_key)
                # Older saves have expiry but no explicit start; preserve their
                # original five-tick electric-field window.
                start = float(start) if start is not None else float(field_expiry) - 5
                active_windows.append((entry[0], start, float(field_expiry)))
            ticks = sum(any(start < tick <= field_expiry
                            for _source, start, field_expiry in active_windows)
                        for tick in tick_range)
            active_sources = {source for source, start, field_expiry in active_windows
                              if any(start < tick <= field_expiry for tick in tick_range)}
            if not ticks:
                continue
            if entity is self.player:
                from .settlement import REASON_ENVIRONMENT, settle_delta
                trauma = self._identity_environment_trauma(ticks, 'electric')
                if active_sources.intersection({"player", "battery", "static_arc", "thunder_orb",
                                                "arc_bolt", "expansion_e07"}):
                    from ..equipment.expansion_runtime import environment_guard
                    trauma = environment_guard(self, "owned_field_damage_and_guard", trauma)
                settle_delta(self, 'lucidity',
                             -trauma,
                             reason=REASON_ENVIRONMENT, source='电场')
            elif entity.relation == "稳定意识":
                # 电场只有玩家电系一个充能来源（actions 充能点唯一）——全部归因。
                damage = ticks
                if active_sources.intersection({"player", "battery", "static_arc", "thunder_orb",
                                                "arc_bolt", "expansion_e07"}):
                    from ..equipment.expansion_runtime import electric_field_damage_bonus
                    damage += electric_field_damage_bonus(self, entity)
                self._npc_scorched(entity, label="电弧", cause_uid="electric",
                                   damage=damage, attributed=True)
            else:
                damage = ticks
                owned = bool(active_sources.intersection({"player", "battery", "static_arc", "thunder_orb",
                                                          "arc_bolt", "expansion_e07"}))
                if owned:
                    from ..equipment.expansion_runtime import electric_field_damage_bonus
                    damage += electric_field_damage_bonus(self, entity)
                _damage_number_before = entity.integrity
                entity.integrity = max(0, entity.integrity-damage)
                from .hit_events import note_integrity_loss
                note_integrity_loss(self, entity, _damage_number_before)
                if owned and entity.integrity > 0:
                    from ..equipment.expansion_runtime import electric_field_slow
                    electric_field_slow(self, entity)
                if entity.integrity <= 0:
                    self._resolve_enemy(entity)
            affected.append(pos)
        if affected:
            self._emit_combat_fx("electric", affected[0], cells)
        self._prune_electric_fields()


    @staticmethod
    def _unstable_seed(totals: dict) -> int:
        # Python string hashes vary by process; material reactions must not.
        return sum((crc32(kind.encode('utf-8')) & 0xFFFF) * amount for kind, amount in totals.items())
    _SPECIAL_WALL_KINDS = frozenset({"烛泪柱", "枕木", "黄粱米堆", "梦晶簇", "蜡化记忆墙", "无意识结晶"})

    def _prime_material_clocks(self, cell: Cell) -> None:
        """A newly arrived material cannot accumulate time before its arrival."""
        liquid = LIQUID_DEFINITIONS.get(cell.liquid_kind) if cell.liquid > 0 else None
        gas = GAS_DEFINITIONS.get(cell.gas_kind) if cell.gas > 0 else None
        active = set()
        if liquid is not None:
            if liquid.flow_period > 1:
                active.add("flow:" + cell.liquid_kind)
            if liquid.evaporation_period > 0:
                active.add("evap:" + cell.liquid_kind)
        if gas is not None:
            active.add("decay:" + cell.gas_kind)
        for key in list(cell.material_clocks):
            if key.startswith(("flow:", "evap:", "decay:")) and key not in active:
                del cell.material_clocks[key]
        for key in active:
            cell.material_clocks.setdefault(key, self.time)

    def _resume_material_clocks(self, snapshot) -> None:
        """Inactive maps freeze their clock remainders rather than aging offscreen."""
        elapsed = max(0, self.time-snapshot.material_time)
        if elapsed:
            for entity in snapshot.enemies:
                if 'last_time' in entity.hospital_state:
                    entity.hospital_state['last_time'] += elapsed
                for key in ('recover_until', 'last_cast_start', 'alert_since', 'summon_expire'):
                    if key in entity.active_skill_state:
                        entity.active_skill_state[key] += elapsed
                # §17：离层生物的时间是冻结的，征兆硬边界与结束保护随暂停一起
                # 顺延，不能因为别层经过的真实回合在回来时被一次性烧掉。
                for table in (entity.portent_deadlines, entity.portent_protection):
                    for key, value in list(table.items()):
                        table[key] = int(value) + elapsed
            for row in snapshot.cells:
                for cell in row:
                    for key in cell.material_clocks:
                        cell.material_clocks[key] += elapsed
        snapshot.material_time = self.time

    def _ensure_material_index(self) -> None:
        """建立材料活动格索引；后续行动只遍历这些格子。"""
        if getattr(self, "_material_index_ready", False):
            return
        liquid: set[tuple[int, int]] = set()
        gas: set[tuple[int, int]] = set()
        flame: set[tuple[int, int]] = set()
        special: set[tuple[int, int]] = set()
        fans: set[tuple[int, int]] = set()
        exhausts: set[tuple[int, int]] = set()
        phases: set[tuple[int, int]] = set()
        for y, row in enumerate(self.cells):
            for x, cell in enumerate(row):
                self._prime_material_clocks(cell)
                position = (x, y)
                if cell.liquid > 0:
                    liquid.add(position)
                if cell.gas > 0:
                    gas.add(position)
                if cell.flame > 0:
                    flame.add(position)
                if (cell.phase_stock or cell.flame > 0
                        or cell.aggregate_variant == '冰面'
                        or (cell.solid and cell.wall_kind in _PHASE_WALL_KINDS)):
                    phases.add(position)
                if cell.wall_kind in self._SPECIAL_WALL_KINDS:
                    special.add(position)
                wall = WALL_DEFINITIONS.get(cell.wall_kind)
                if cell.solid and cell.integrity > 0 and wall is not None:
                    if wall.gas_push_direction:
                        fans.add(position)
                    if wall.gas_dissipation_multiplier > 1:
                        exhausts.add(position)
        self._liquid_cells = liquid
        self._gas_cells = gas
        self._periodic_liquid_cells = {p for p in liquid
            if LIQUID_DEFINITIONS.get(self.cell(*p).liquid_kind)
            and LIQUID_DEFINITIONS[self.cell(*p).liquid_kind].evaporation_period > 0}
        self._periodic_gas_cells = {p for p in gas
            if GAS_DEFINITIONS.get(self.cell(*p).gas_kind)
            and GAS_DEFINITIONS[self.cell(*p).gas_kind].dissipation_period > 0}
        self._flame_cells = flame
        self._phase_cells = phases
        self._special_cells = special
        self._ventilation_cells = fans
        self._exhaust_cells = exhausts
        self._material_index_ready = True

    def _reset_material_index(self) -> None:
        """换幅时作废材料索引：旧地图的坐标在新地图上没有意义。

        索引是惰性重建的运行期缓存（见 _ensure_material_index），可
        ``self.cells`` 被整幅替换（换梦层、进出梦中梦）并不会让它自动失效。
        残留的旧坐标会让按索引取格的结算（_simulate_materials 等）在新地图上
        直接越界——窄图对宽图时必然踩到。
        """
        self._material_index_ready = False
        self._liquid_cells = set()
        self._gas_cells = set()
        self._periodic_liquid_cells = set()
        self._periodic_gas_cells = set()
        self._flame_cells = set()
        self._phase_cells = set()
        self._special_cells = set()
        self._ventilation_cells = set()
        self._exhaust_cells = set()

    def _sync_material_position(self, x: int, y: int, *, prime: bool = True) -> None:
        """同步单格索引；用于材料转移及墙体/火焰变化。

        prime=False 只给已经在本拍内调用过 _prime_material_clocks 的写入路径用
        （_add_liquid/_add_gas），避免同一格每拍重复建时钟集合。
        """
        self._ensure_material_index()
        position = (x, y)
        cell = self.cell(x, y)
        if prime:
            self._prime_material_clocks(cell)
        liquid_definition = LIQUID_DEFINITIONS.get(cell.liquid_kind) if cell.liquid > 0 else None
        gas_definition = GAS_DEFINITIONS.get(cell.gas_kind) if cell.gas > 0 else None
        ventilation = exhaust = False
        if cell.solid and cell.integrity > 0:
            wall = wall_def(cell.wall_kind)
            ventilation = bool(wall.gas_push_direction)
            exhaust = wall.gas_dissipation_multiplier > 1
        active_flags = (
            ("_liquid_cells", cell.liquid > 0),
            ("_gas_cells", cell.gas > 0),
            ("_periodic_liquid_cells", liquid_definition is not None
             and liquid_definition.evaporation_period > 0),
            ("_periodic_gas_cells", gas_definition is not None
             and gas_definition.dissipation_period > 0),
            ("_flame_cells", cell.flame > 0),
            ("_phase_cells", bool(cell.phase_stock) or cell.flame > 0
             or cell.aggregate_variant == '冰面'
             or (cell.solid and cell.wall_kind in _PHASE_WALL_KINDS)),
            ("_special_cells", cell.wall_kind in self._SPECIAL_WALL_KINDS),
            ("_ventilation_cells", ventilation),
            ("_exhaust_cells", exhaust),
        )
        for key, active in active_flags:
            bucket = getattr(self, key)
            if active:
                bucket.add(position)
            else:
                bucket.discard(position)

    def _set_flame(self, x: int, y: int, amount: int) -> None:
        self.cell(x, y).flame = max(0, amount)
        if amount <= 0:
            # 火熄了，玩家点燃册同步除名（§4.4：责任跟着火走，火灭责清）。
            self._ignition_owner.get(self.layer_key(), set()).discard((x, y))
        self._sync_material_position(x, y)

    def developed_for_depth(self) -> set[tuple[int, int]]:
        """本层已显影格：显影液流过的地形，永远留在地图上（不含实体/物品）。"""
        return self.developed_cells.setdefault(str(self.depth), set())

    def mark_developed(self, x: int, y: int) -> bool:
        """把一格标记为已显影；返回它是不是新显影的（用于累计与提示）。"""
        developed = self.developed_for_depth()
        if (x, y) in developed:
            return False
        developed.add((x, y))
        self.developed_total += 1
        if self.developed_total >= 10:
            # 「双读」现已是开局自带的天生洞察（见 content.INNATE_INSIGHTS），
            # 这里再授予一次只会静默补位、不发提示——保留调用是为了「双读」
            # 万一不再天生时，显影 10 格这条旧获取通道仍在。
            self._grant_insight("双读")
        return True

    def _mark_developing_liquid(self) -> int:
        """把「此刻正浸着显影液」的格子标成已显影——显影液淌到哪里，哪里的
        地形就永久显形（不分敌我、不受视野限制）；液体继续流，就继续显影。
        """
        newly = 0
        self._ensure_material_index()
        # 2026-09-19 性能改造：只扫有液体的格子（索引快照）。
        for x, y in tuple(self._liquid_cells):
            cell = self.cells[y][x]
            if cell.liquid_kind == "显影液" and cell.liquid > 0 and self.mark_developed(x, y):
                newly += 1
        if newly:
            self.messages.append(tr("显影液淌过 {count} 格，它们的地形留在了视野里。", count=newly))
        return newly

    def puzzle_projectile_blocked(self, x, y):
        """Sealed realm blocks stop bullets before integrity or penetration changes."""
        return (self.cell(x, y).solid and (
            self.realm_id == 'ember_bridge' or
            (self.realm_id == 'toy_memories' and bool(self.circuit_boards))))

    @staticmethod
    def wall_break_noise_radius(definition) -> int:
        """破墙声径：由厚度/高度/硬度与碎裂方式决定，特殊墙体明显更响。"""
        radius = (5 + int(getattr(definition, "thickness", 1) or 1) * 2
                  + max(0, int(getattr(definition, "height", 1) or 1) - 1)
                  + max(0, int(getattr(definition, "hardness", 1) or 1) // 2))
        special = {
            "shatter": 6,            # 尖啸瓷墙：高频碎裂，传得很远
            "void_spores": 4,        # 千层叠岩
            "millennium_summon": 7,  # 蓝屏终端/主机
            "dreamcrystal": 3,       # 梦晶簇
            "summon": 3,             # 回魂陶俑
            "explode": 3,            # 不稳定燃料墙
            "whisper": 2,            # 静默碑岩/回响黑曜岩
            "popup_drop": 3,         # 弹窗墙
        }
        radius += special.get(str(getattr(definition, "break_effect", "")), 0)
        return max(4, min(18, radius))

    def destroy_wall(
        self,
        x: int,
        y: int,
        cause: str,
        triggered: set[tuple[int, int]] | None = None,
        *,
        integrity_before: int | None = None,
    ) -> bool:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        cell = self.cell(x, y)
        if not cell.solid:
            return False
        if cause == 'projectile' and self.puzzle_projectile_blocked(x, y):
            return False
        if cell.wall_kind == "理念立方体":
            return False
        if self.realm_id == "toy_memories" and self.circuit_boards:
            # §12 F：弧光灯架会改造箱体墙格，箱体仍是箱体——解谜期间一并不可拆，
            # 否则「把箱壁换成灯架」就成了破墙捷径。
            from ..materials import LIGHT_FIXTURE_KINDS
            if (cell.wall_kind == "玩具箱壁" or cell.wall_kind in LIGHT_FIXTURE_KINDS
                    or self.circuit_node_at(x, y)):
                return False  # puzzle walls and components cannot be demolished
        triggered = triggered if triggered is not None else set()
        # 回魂陶俑（扩展包 v1）：破坏时放出一只已解决普通异象残影（1 耐久）。
        if (x, y) in triggered:
            return False
        triggered.add((x, y))
        definition = wall_def(cell.wall_kind)
        # 2026-10-25：玩家用子弹或推动打碎「完整度超过 150」的墙体，崩解度 +1。
        # 只认这两种原因；徒手/构想/爆炸/燃烧/侵蚀/敌方破墙等一律不增长。
        if (cause in ("projectile", "push")
                and max(int(cell.integrity), int(definition.integrity),
                        int(integrity_before or 0)) > 150):
            self._add_wall_break_dissolution(definition.name)
        # §11 §7 灰烬记忆：只有亲眼看碎裂才记录轮廓；看不见的碎裂仅留声音线索。
        witnessed = bool(self.is_visible(x, y))
        self.clear_wall(cell)
        if definition.break_effect == "smoke":
            self._add_gas(cell, "黑烟", 50)
        elif definition.break_effect == "condense":
            self._add_liquid(cell, "水", 100)
            self._add_gas(cell, "水蒸气", 60)
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < self.width and 0 <= ny < self.height and not self.cell(nx, ny).solid:
                    self._add_liquid(self.cell(nx, ny), "水", 35)
        elif definition.break_effect == "soak":
            # 潮解纸墙：破坏后在原格留下纸浆，形成"拆墙→淌浆→点火"连锁。
            self._add_liquid(cell, "纸浆", 30)
        elif definition.break_effect == "ink":
            self._add_liquid(cell, "黑墨", 25)
        elif definition.break_effect == "shatter":
            # 尖啸瓷墙：灰尘云 + 碎瓷伤及相邻者（包括玩家自己）。
            self._add_gas(cell, "灰尘云", 40)
            if witnessed and self.insight_active("灰烬记忆"):
                from .vision.knowledge import record_terrain_cells
                outline = [(x, y)]
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if (0 <= nx < self.width and 0 <= ny < self.height
                            and not self.cell(nx, ny).solid):
                        outline.append((nx, ny))
                record_terrain_cells(self, outline)
                self.messages.append(tr("碎裂的地形深深刻进灰烬记忆。"))
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                victim = self.entity_at(nx, ny)
                if victim is self.player:
                    from .settlement import REASON_ENVIRONMENT, settle_delta
                    settle_delta(self, 'lucidity', -1,
                                 reason=REASON_ENVIRONMENT, source='尖啸瓷墙碎片')
                    if self.insight_active("灰烬记忆"):
                        self._ash_memory_reward(x, y)
                    else:
                        self.messages.append(tr("碎瓷划过你，清醒度 −1。"))
                elif victim is not None:
                    _damage_number_before = victim.integrity
                    victim.integrity = max(0, victim.integrity - 1)
                    from .hit_events import note_integrity_loss
                    note_integrity_loss(self, victim, _damage_number_before)
                    if victim.integrity <= 0:
                        self._resolve_enemy(victim)
        elif definition.break_effect == "summon":
            # 回魂陶俑（扩展包 v1）：放出一只已解决普通异象残影（1 耐久，警戒）。
            from .content import ORDINARY_ANOMALY_IDS

            solved = [cid for cid in self.kills_by_kind
                      if cid in ANOMALY_DEFINITIONS
                      and ANOMALY_DEFINITIONS[cid].get("anomaly_kind") == "普通异象"
                      and not ANOMALY_DEFINITIONS[cid].get("spawn_only")]
            pool_id = solved[0] if solved else "anomaly.page_hound"
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < self.width and 0 <= ny < self.height and not self.cell(nx, ny).solid:
                    echo = self.add_defined_enemy(pool_id, nx, ny)
                    echo.integrity = 1
                    echo.alert_state = "追踪"
                    break
            self.messages.append(tr("陶俑碎裂——一个残影从碎片中站起。"))
        elif definition.break_effect == "explode":
            self._add_gas(cell, "可燃气体", 50)
            self._explode(x, y, 1, 2, triggered)
        elif definition.break_effect == "whisper":
            # 静默碑岩/回响黑曜岩：放出呢喃。
            self._add_gas(cell, "呢喃", 60)
        elif definition.break_effect == "void_spores":
            # 千层叠岩：放出虚无孢子。
            self._add_gas(cell, "虚无孢子", 70)
        elif definition.break_effect == "dreamcrystal":
            # 梦晶簇：被破坏后放出全部储存的气体。
            if cell.cover > 0 and cell.gas_kind:
                kind = cell.gas_kind
                stored = cell.material_clocks.pop('crystal_stored:' + kind,self.time)
                mark = cell.material_clocks.pop('crystal_decay:' + kind,stored)
                self._add_gas(cell, kind, cell.cover,
                              decay_mark=self.time-max(0,stored-mark))
                self.messages.append(tr("梦晶簇碎裂，储存的气体尽数涌出。"))
            cell.cover = 0
        elif definition.break_effect == "millennium_summon":
            # 蓝屏终端（零点体育场 §10.3 路径 B）：砸了它的主机——敌对千年虫登场。
            self._spawn_millennium_worm()
        elif definition.break_effect == "popup_drop":
            # 弹窗墙（千禧园）：关不掉的弹窗炸出一封「未读消息 99+」。
            from .entities import WorldItem as _WorldItem

            self.world_items.append(_WorldItem(self._make_item("unread_99"), x, y))
            self.messages.append(tr("弹窗炸开——掉出一封「未读消息 99+」。"))
        # §11 H1 真实声源（R 值按 docs 261022 §5.3 首轮建议）：普通硬墙被徒手／
        # 投射物／构想实际破坏时发 5 格脉冲；尖啸瓷墙以自己的 9 格碎裂声代替，
        # 不再叠加普通破墙声。爆炸导致的破墙不重复发声（爆心已有自己的脉冲），
        # 软性融蚀与自然消失保持无声。
        noise = self.wall_break_noise_radius(definition)
        player_causes = ("hand", "projectile", "ability", "push", "spool",
                         "carve", "world_tamper")
        if definition.break_effect == "shatter":
            self._sound_pulse(x, y, noise, by_player=cause in player_causes,
                              category="porcelain", source=tr("尖啸瓷墙碎裂"),
                              triggers_rewards=False)
        elif cause in (*player_causes, "enemy_breach"):
            self._sound_pulse(x, y, noise, by_player=cause in player_causes,
                              category="wall_break", source=tr(definition.name),
                              triggers_rewards=False)
        from .tactical_layouts import note_gate_breach
        note_gate_breach(self,x,y,cause)
        # 墙体破坏改变可听拓扑：挂起的调查任务在下一回合重新尝试寻路。
        self.topology_revision += 1
        return True

    def _ash_memory_reward(self, x: int, y: int) -> None:
        """同一层同一墙格的灰烬记忆只结算一次（重建也不重复发放）。"""
        key = f"{self.layer_key()}:{int(x)},{int(y)}"
        if key in self.ash_memory_settled:
            self.messages.append(tr("碎瓷划过你，清醒度 −1。"))
            return
        self.ash_memory_settled.append(key)
        self.restore_resource('imagination', 3)
        self.messages.append(tr("碎瓷擦身而过，灰烬记忆把余烬换成了 3 点想象力。"))

    def _psyche_suffix(self) -> str:
        """混乱化改造（2026-10-15）：心智/想象跌进「危险」「紧急」档时，
        给爆炸等大效果消息追加失控横幅——让「状态越低、场面越失控」看得见。
        健康/受损档返回空串。"""
        tier = max(self.mind_tier, self.lucidity_tier)
        if tier >= 3:
            return tr("【梦境·紧急：彻底失控！】")
        if tier == 2:
            return tr("【梦境·危险：效果开始失控】")
        return ""

    def _explode(
        self,
        cx: int,
        cy: int,
        radius: int,
        power: int,
        triggered: set[tuple[int, int]] | None = None,
        from_player: bool = False,
    ) -> None:
        if from_player:
            self._kill_full_reward = True
        triggered = triggered if triggered is not None else set()
        disorder = self.physics_modifiers()["explosion_bonus"]
        effective_power = power + disorder
        from ..equipment.expansion_runtime import (
            blast_guard, consume_feedback_for_blast_slow, explosion_damage_bonus,
        )
        enemy_bonus, self_bonus = explosion_damage_bonus(self, from_player)
        blast_slow_used = False
        affected = 0
        ignition: list[tuple[int, int]] = []
        from .throwing import flight_path
        # 取爆炸前的遮挡图；同一冲击波不能在破墙后穿透这堵墙。
        opaque = {(x, y) for y in range(max(1, cy-radius), min(self.height-1, cy+radius+1))
                  for x in range(max(1, cx-radius), min(self.width-1, cx+radius+1))
                  if self.cell(x, y).solid and self.cell(x, y).height >= 2}
        hit_entities: set[int] = set()
        cells_marked: set[tuple[int, int]] = set()
        for y in range(max(1, cy - radius), min(self.height - 1, cy + radius + 1)):
            for x in range(max(1, cx - radius), min(self.width - 1, cx + radius + 1)):
                if abs(x - cx) + abs(y - cy) > radius:
                    continue
                path = [(cx, cy), *flight_path((cx, cy), (x, y))]
                if (any(pos in opaque for pos in path[1:-1]) or any(
                        a[0] != b[0] and a[1] != b[1]
                        and (a[0], b[1]) in opaque and (b[0], a[1]) in opaque
                        for a, b in zip(path, path[1:]))):
                    continue
                cells_marked.add((x, y))
                cell = self.cell(x, y)
                if cell.solid:
                    instability = self.physics_modifiers().get("instability", 0)
                    cell.integrity = max(0, cell.integrity - effective_power * 30 - instability * 25)
                    if cell.integrity == 0:
                        self.destroy_wall(x, y, "explosion", triggered)
                    continue
                # 爆炸引燃：半径内可燃地面（液体/气体/植物）当场起火，
                # 绝热层/梦境绒毯等防火地板除外（fireproof 阻燃）。
                if self._cell_is_flammable(cell) and not floor_fireproof(cell):
                    ignition.append((x, y))
                entity = self.entity_at(x, y)
                if (entity and entity is not self.player and entity.relation != "稳定意识"
                        and id(entity) not in hit_entities):
                    hit_entities.add(id(entity))
                    if from_player:
                        self._kill_full_reward = True
                    damage = max(1, effective_power * 2 - max(0, abs(x-cx)+abs(y-cy)-1)
                                 + enemy_bonus)
                    _damage_number_before = entity.integrity
                    entity.integrity = max(0, entity.integrity - damage)
                    from .hit_events import note_integrity_loss
                    note_integrity_loss(self, entity, _damage_number_before)
                    affected += 1
                    # 冲击推动（设计文档 §9.4）：实体被推离爆心 1 格——
                    # 沿爆心→实体方向找开放格，推得动才推（撞墙不动）。
                    push_x = max(-1, min(1, entity.x - cx))
                    push_y = max(-1, min(1, entity.y - cy))
                    if push_x or push_y:
                        nx, ny = entity.x + push_x, entity.y + push_y
                        if (
                            0 <= nx < self.width and 0 <= ny < self.height
                            and not self.cell(nx, ny).solid
                            and self.entity_at(nx, ny) is None
                        ):
                            entity.x, entity.y = nx, ny
                    if entity.integrity > 0:
                        blast_slow_used = consume_feedback_for_blast_slow(
                            self, entity, blast_slow_used)
                    if entity.integrity <= 0:
                        self._resolve_enemy(entity)
                # 玩家自伤（扩展设计 2026-09-22）：爆炸不绕开玩家——半径内吃
                # effective_power 点清醒创伤（凤凰羽衣免疫，不被推离）。
                if self.entity_at(x, y) is self.player and effective_power > 0:
                    if not self._effect_power("fire_ward"):
                        trauma = max(1, effective_power + self_bonus
                                     - min(1, self._effect_power("blast_padding")))
                        if from_player:
                            trauma = blast_guard(self, True, trauma)
                        from .settlement import REASON_ENVIRONMENT, settle_delta
                        settle_delta(self, 'lucidity', -trauma,
                                     reason=REASON_ENVIRONMENT, source='爆炸冲击')
                        self.messages.append(tr("冲击波扫过你，清醒度 −{n}。", n=trauma))
        # §4.4 归因：玩家亲手引爆（from_player）或爆心本是玩家点的火——
        # 波及引燃的格子进点燃册（蔓延同责），异象/自然爆炸不归因。
        blast_attribution = bool(from_player) or (
            (cx, cy) in self._ignition_owner.get(self.layer_key(), set()))
        for x, y in ignition:
            self._ignite_cell(x, y, 3, attribute_player=blast_attribution)
        self._material_index_ready = False
        # 爆炸动画标记（运行期缓存，不入档）：UI 按帧渐隐黄→红高亮。
        self._emit_combat_fx("explosion", (cx, cy), cells_marked)
        # 并集累积（2026-09-22）：连锁爆炸的每一圈都显示，不再被最后一次覆盖。
        existing = getattr(self, "explosion_cells", None) or set()
        self.explosion_cells = existing | cells_marked
        # 每次新爆炸都归零动画年龄——连锁未结束时动画不老化。
        self.explosion_age = 0
        # 记录爆心与半径（渲染按距离渐变取色）。
        blasts = getattr(self, "explosion_blasts", None)
        if blasts is None:
            self.explosion_blasts = blasts = []
        blasts.append((cx, cy, radius))
        # §11 H1：真实爆炸在爆心发普通警戒脉冲（不自动强诱引，也不触发
        # 主动发声的装备连击／回声控制奖励）。基础声径随实际半径增长。
        self._sound_pulse(cx, cy, max(8, 2 * radius + 4), by_player=bool(from_player),
                          category="explosion", source=tr("爆炸"),
                          triggers_rewards=False)
        self.messages.append(tr("冲击折页爆发，影响 {count} 个失控意识。", count=affected)
                             + self._psyche_suffix())

    def _remote_overwrite(self) -> None:
        self.overwrite_count += 1
        radius = max(4, min(self.width, self.height) // 3)
        rng = random.Random(self.seed + self.depth * 1009 + self.overwrite_count * 9176)
        liquid_choices = tuple(k for k, d in LIQUID_DEFINITIONS.items()
                               if not d.spawn_realms or self.realm_id in d.spawn_realms)
        gas_choices = tuple(k for k, d in GAS_DEFINITIONS.items()
                            if not d.spawn_realms or self.realm_id in d.spawn_realms)
        changed = 0
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                distance = abs(x - self.player.x) + abs(y - self.player.y)
                if distance <= radius or rng.random() > 0.12:
                    continue
                if rng.random() < 0.18:
                    # 远程覆写只生成内部墙材；意识边界与地面容器必须排除——
                    # 前者永远留在最外圈，后者离开内容物只是空罐。
                    wall_choices = tuple(
                        kind for kind, definition in WALL_DEFINITIONS.items()
                        if kind != "意识边界" and kind not in CONTAINER_KINDS
                        and (not definition.spawn_realms or self.realm_id in definition.spawn_realms)
                    )
                    kind = wall_choices[rng.randrange(len(wall_choices))]
                    self._overwrite_cell(x, y, wall_kind=kind)
                else:
                    liquid_kind = rng.choice(liquid_choices) if rng.random() < 0.08 else ""
                    gas_kind = rng.choice(gas_choices) if rng.random() < 0.08 else ""
                    self._overwrite_cell(x, y, wall_kind=None, liquid_kind=liquid_kind, gas_kind=gas_kind)
                changed += 1
        if changed:
            self.messages.append(tr("清醒度归零，远域覆写永久改变了 {count} 个格子。", count=changed))

    def _overwrite_cell(
        self,
        x: int,
        y: int,
        wall_kind: str | None,
        liquid_kind: str = "",
        gas_kind: str = "",
    ) -> None:
        cell = self.cell(x, y)
        if wall_kind is not None:
            # 特殊墙材必须暴露在空气侧；远程覆写也不能把它塞进墙体核心。
            if wall_kind in {"反光玻璃墙", "冷凝囊壁", "不稳定燃料墙"}:
                exposed = any(
                    0 <= nx < self.width
                    and 0 <= ny < self.height
                    and not self.cell(nx, ny).solid
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                )
                if not exposed:
                    wall_kind = "压实聚合墙"
            released_liquid = ("", 0)
            released_gas = ("", 0)
            released_gas_mark = None
            if cell.solid:
                self.destroy_wall(x, y, "remote_overwrite")
                released_liquid = (cell.liquid_kind, cell.liquid)
                released_gas = (cell.gas_kind, cell.gas)
                if cell.gas > 0:
                    self._prime_material_clocks(cell)
                    released_gas_mark = cell.material_clocks.get('decay:' + cell.gas_kind,self.time)
            self.configure_wall(cell, wall_kind)
            self._prime_material_clocks(cell)
            self._redistribute_overwrite_products(x, y, released_liquid, released_gas,
                                                  gas_decay_mark=released_gas_mark)
            return
        if cell.solid:
            self.destroy_wall(x, y, "remote_overwrite")
        else:
            self.clear_wall(cell)
            cell.liquid = 0
            cell.liquid_kind = ""
            cell.gas = 0
            cell.gas_kind = ""
            cell.flame = 0
        if liquid_kind:
            self._add_liquid(cell, liquid_kind, 100)
        if gas_kind:
            self._add_gas(cell, gas_kind, 100)

    def _redistribute_overwrite_products(
        self,
        x: int,
        y: int,
        liquid: tuple[str, int],
        gas: tuple[str, int],
        *, gas_decay_mark: int | None = None,
    ) -> None:
        targets = [
            (nx, ny)
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            if 0 <= nx < self.width and 0 <= ny < self.height and not self.cell(nx, ny).solid
        ]
        if not targets:
            return
        for (kind, amount), add_material, flags in (
            (liquid,self._add_liquid,{}), (gas,self._add_gas,{'decay_mark':gas_decay_mark}),
        ):
            if not kind or amount <= 0:
                continue
            base, remainder = divmod(amount, len(targets))
            for index, (nx, ny) in enumerate(targets):
                share = base + (1 if index < remainder else 0)
                if share:
                    add_material(self.cell(nx, ny), kind, share, **flags)

    # 每拍预算上限（2026-09-19）：液/气源单拍最多处理的格数。常规地图
    # （几百～一两千活动格）永远不会触顶；只有极少数高改动场景（大片燃烧、
    # 巨型液体湖）才会超额，超出部分延迟到下一拍继续处理。
    SIM_SOURCE_BUDGET = 6000  # 混乱化改造（2026-10-15）：4000→6000，高改动场景更少延迟
    # 全图校准扫描周期：增量索引每 50 回合做一次全图重扫自愈，兜住任何
    # 漏同步的索引漂移（正常情况下增量同步已经精确）。
    FULL_INDEX_SCAN_INTERVAL = 50

    def _simulate_materials(self, amount: int) -> None:
        """Run synchronous material passes; low lucidity adds discrete instability."""
        instability = self.lucidity_tier
        passes = min(4, max(1, amount + instability))
        # 50 回合一次的全图校准：强制重建活动格索引（自愈兜底）。
        if self.time - getattr(self, "_last_full_scan_time", -(10 ** 9)) >= self.FULL_INDEX_SCAN_INTERVAL:
            self._material_index_ready = False
            self._last_full_scan_time = self.time
        self._ensure_material_index()
        # §14.6：台体被破坏后，台上显化物落回地面（只换承接关系，不复制）。
        self.normalize_world_item_surfaces()
        exposed_gas: set[tuple[int, int]] = set()
        from .content import item_is_flammable
        item_fuel_cells = {(entry.x, entry.y) for entry in self.world_items
                           if item_is_flammable(entry.item)}
        for _ in range(passes):
            self._simulate_liquid_pass()
            self._simulate_special_materials()
            self._simulate_recipe_reactions()
            exposed_gas.update(self._simulate_gas_pass())
            flame_targets: list[tuple[int, int]] = []
            # 2026-10-15 混乱化改造：蔓延强度真正接入 fire_spread_bonus——
            # 心智越失序，每火源每拍点燃的邻格越多（健康 2 格 → 紧急 8 格）。
            fire_spread = self.physics_modifiers()["fire_spread_bonus"]
            # 2026-09-19 性能改造：火焰蔓延只扫「当前着火的格子」（索引快照），
            # 不再每拍全图重建。快照语义与旧全图扫描一致：本拍新增的火不影响
            # 本拍的蔓延候选。
            for x, y in tuple(self._flame_cells):
                cell = self.cell(x, y)
                if cell.flame <= 0:
                    continue
                neighbors = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
                open_neighbors = [
                    (nx, ny)
                    for nx, ny in neighbors
                    if 0 <= nx < self.width and 0 <= ny < self.height
                ]
                if not open_neighbors:
                    continue
                candidates = [
                    (nx, ny)
                    for nx, ny in open_neighbors
                    if (self._cell_is_flammable(self.cell(nx, ny))
                        or (nx, ny) in item_fuel_cells)
                    and not floor_fireproof(self.cell(nx, ny))
                ]
                for target in candidates[: 2 + 2 * fire_spread]:
                    flame_targets.append(((x, y), target))
            owner_cells = self._ignition_owner.get(self.layer_key(), set())
            for source, target in flame_targets:
                # 统一点燃入口：蔓延遇到高浓度可燃气同样会引爆（连锁）。
                # §4.4 归因：玩家点的火蔓延出去仍是玩家的责任——蔓延格继承
                # 源格的点燃册标记，但不算「亲手点燃」（by_player 副作用不触发）。
                self._ignite_cell(target[0], target[1], 3,
                                  attribute_player=source in owner_cells)
        # 地板按客观回合结算，不随低清醒造成的额外材料模拟拍重复触发。
        self._simulate_fire_damage(amount)
        self._tick_electric_fields(amount)
        self._simulate_new_floors(amount)
        # 显影液在这次流动里浸过的格子 → 永久显影（在挥发结算之前取样，
        # 这样刚被液体漫过、随后又干掉的格子同样算「流过」）。
        self._mark_developing_liquid()
        self._apply_liquid_evaporation(instability)
        self._simulate_ventilation(amount)
        # 2026-09-19 性能改造：暴露气收集只扫有气的格子（索引快照）。
        for x, y in tuple(self._gas_cells):
            cell = self.cell(x, y)
            if cell.gas and any(
                0 <= nx < self.width and 0 <= ny < self.height and not self.cell(nx, ny).solid
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            ):
                exposed_gas.add((x, y))
        self._apply_gas_dissipation(exposed_gas, instability)
        # 拨号音连通气团的周期性短音：按客观世界回合节拍，不按额外材料拍重复触发。
        self._simulate_dial_tone_regions(amount)
        # 燃烧消耗燃料（2026-09-18）：可燃液体/气体被烧每拍 −3，烧干后
        # 火焰只能靠余温烧完（不再永燃）；水与其它灭火液体直接扑灭本格火焰
        # （液氦走 extinguishes_fire 旗标；水 ≥10 即浇熄——与既有的
        # 「30% 概率转灼热蒸汽」并存：大多数水直接灭火，偶尔腾起蒸汽）。
        # 2026-09-19 性能改造：只扫当前着火的格子（索引快照），逐格增量同步。
        self._simulate_fire_fuel(amount)
        # 相变按世界时间节拍，且排在火焰结算之后：水先有机会灭火，
        # 再考虑是否被热度蒸发；额外的失序材料拍不得加速相变。
        from .phase_changes import tick as tick_phase_changes
        tick_phase_changes(self)

    def _dial_tone_cell(self, x: int, y: int) -> bool:
        """这一格是否属于「够浓的拨号音」（连通区域的成员条件）。"""
        cell = self.cell(x, y)
        return (cell.gas > 0 and cell.gas_kind == DIAL_TONE_GAS
                and cell.gas >= DIAL_TONE_MIN_AMOUNT)

    def _simulate_dial_tone_regions(self, amount: int = 1) -> None:
        """§13.2 拨号音：浓度≥12 的四邻连通气团每 4 世界回合发一次 R3。

        一个连通区域只登记一个稳定声源（取区域内最小坐标，与遍历顺序无关）；
        破碎的少量气体不到浓度门槛就不发声。一次跨多个节拍的世界推进（等待数回合）
        仍然只发一次：这是环境声源，不是每格每拍的 AI 刷新风暴。
        只读材料状态，不碰 `dial_in` 的既有拨号事件计时。
        """
        if amount <= 0:
            return
        if self.time // DIAL_TONE_PERIOD == max(0, self.time - amount) // DIAL_TONE_PERIOD:
            return
        self._ensure_material_index()
        pending = {pos for pos in self._gas_cells if self._dial_tone_cell(*pos)}
        while pending:
            origin = min(pending)
            region = {origin}
            queue = [origin]
            while queue:
                x, y = queue.pop()
                for pos in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if pos in region:
                        continue
                    nx, ny = pos
                    if not (0 <= nx < self.width and 0 <= ny < self.height):
                        continue
                    if pos in pending:
                        region.add(pos)
                        queue.append(pos)
            pending -= region
            ax, ay = min(region)
            self._sound_pulse(ax, ay, DIAL_TONE_RADIUS, category="environment",
                              source=tr(DIAL_TONE_GAS), announce=False)

    def _simulate_fire_fuel(self, amount: int = 1) -> None:
        """燃料按客观回合消耗，额外材料流动拍不加快燃烧。"""
        self._ensure_material_index()
        from .content import item_is_flammable
        for _ in range(max(0, amount)):
            self._simulate_fire_burn_items()
            item_positions = {(entry.x, entry.y) for entry in self.world_items
                              if item_is_flammable(entry.item)}
            for x, y in tuple(self._flame_cells):
                cell = self.cell(x, y)
                if cell.flame <= 0:
                    continue
                liquid = LIQUID_DEFINITIONS.get(cell.liquid_kind)
                if (floor_fireproof(cell) or (cell.liquid >= 10 and
                    (cell.liquid_kind == "水" or (liquid and liquid.extinguishes_fire)))):
                    self._set_flame(x, y, 0)
                    continue
                if plant_burns(cell.plant):
                    if cell.plant_fuel <= 0:
                        cell.plant_fuel = 12 if cell.plant == 2 else 6
                    cell.plant_fuel = max(0, cell.plant_fuel - 3)
                    if not cell.plant_fuel:
                        burned_plant = self.set_plant(x, y, 0)
                        if burned_plant:
                            self._note_plant_wither(x, y, burned_plant, "burned")
                burned_floor = floor_effect_for(cell).burns_to
                if burned_floor:
                    cell.floor_fuel = max(0, (cell.floor_fuel or 12) - 3)
                    if not cell.floor_fuel:
                        cell.aggregate_variant = burned_floor
                wall = WALL_DEFINITIONS.get(cell.wall_kind)
                if wall and wall.flammable and self._wall_can_burn(x, y):
                    cell.integrity = max(0, cell.integrity - (2 if cell.wall_kind == "蜡化记忆墙" else 4))
                    if not cell.integrity:
                        kind = cell.wall_kind
                        if cell.solid:
                            self.destroy_wall(x, y, "burn")
                        else:
                            self.clear_wall(cell)
                        if kind == "烛泪柱":
                            flame = cell.flame
                            self.configure_wall(cell, "灰烬")
                            self._set_flame(x, y, flame)
                        if kind in ("蜡化记忆墙", "烛泪柱"):
                            self._add_liquid(cell, "熔融蜡烛", 20)
                        elif kind == "枕木":
                            self._add_gas(cell, "安眠香", 40)
                        elif kind == "黄粱米堆":
                            self._add_gas(cell, "催眠雾", 30)
                liquid = LIQUID_DEFINITIONS.get(cell.liquid_kind)
                if liquid and liquid.flammable and cell.liquid:
                    cell.liquid = max(0, cell.liquid - 3)
                    if not cell.liquid:
                        cell.liquid_kind = ""
                gas = GAS_DEFINITIONS.get(cell.gas_kind)
                if gas and gas.flammable and cell.gas:
                    cell.gas = max(0, cell.gas - 3)
                    if not cell.gas:
                        cell.gas_kind = ""
                fueled = self._cell_is_flammable(cell, liquid_min=1) or (x, y) in item_positions
                self._set_flame(x, y, max(cell.flame, 2) if fueled else max(0, cell.flame - 1))
                self._sync_material_position(x, y)

    def _wall_can_burn(self, x: int, y: int) -> bool:
        return not (self.cell(x, y).wall_kind == "理念立方体" or self.circuit_node_at(x, y)
                    or (self.realm_id == "toy_memories" and self.cell(x, y).wall_kind == "玩具箱壁"))

    # 高浓度可燃气引爆阈值（设计文档：高浓度挥发性弥散印象遇火源爆炸）。
    GAS_DETONATION_THRESHOLD = 60

    def _ignite_cell(self, x: int, y: int, strength: int = 2, chain: set | None = None,
                     by_player: bool = False, *, liquid_min: int = 1,
                     attribute_player: bool = False) -> bool:
        """统一点燃入口（2026-09-18 触发机制补全）。

        之前点燃散落五处（蓝端火柴/保温杯余热/火花构想/火焰蔓延/爆炸引燃），
        各写各的 flame 值；现在全部收拢到这里，规则只有一份：

        - 防火地板（绝热层/梦境绒毯）与不可燃格：点不着，返回 False；
        - 高浓度可燃气（≥ GAS_DETONATION_THRESHOLD 且该气体 flammable）：
          **气爆**——仅消耗 12 单位气体，余量继续燃烧，按浓度档引爆
          （<50 半径 1 / <100 半径 2 / ≥100 半径 3，威力 2 + 心智失序档），
          气爆经 ``chain`` 防重入
          （连锁气爆是特性，同一片燃烧中的气体不重复引爆）；
        - 普通可燃格：flame 提升到 strength（上限 8）。

        ``by_player=True`` 表示**玩家亲手**点的火（道具/构想/攻击附燃/投掷），
        火焰蔓延、异象放火与爆炸连锁都不传这个标记——灰烬撤步只认亲手那次。

        ``attribute_player=True`` 是 §4.4 的**归因标记**（与 by_player 分立）：
        玩家点的火蔓延/引爆波及到的格子进「玩家点燃册」（_ignition_owner），
        烧到稳定意识时可归因警告——但**不**触发 by_player 的亲手副作用
        （身份点燃计数/灰烬撤步只认亲手那次，蔓延不算）。异象放火两者都不传。
        """
        cell = self.cell(x, y)
        if not self._cell_is_flammable(cell, liquid_min=liquid_min):
            from .content import item_is_flammable
            if not any(entry.x == x and entry.y == y and item_is_flammable(entry.item)
                       for entry in self.world_items):
                return False
        if cell.wall_kind and not self._wall_can_burn(x, y):
            return False
        if floor_fireproof(cell):
            return False
        definition = GAS_DEFINITIONS.get(cell.gas_kind) if cell.gas_kind else None
        if (
            cell.gas >= self.GAS_DETONATION_THRESHOLD
            and definition is not None
            and definition.flammable
            and cell.flame <= 0
        ):
            chain = chain if chain is not None else set()
            if (x, y) in chain:
                return False
            chain.add((x, y))
            concentration = cell.gas
            cell.gas = max(0, cell.gas - 12)
            self._set_flame(x, y, min(8, max(2, strength)))
            if by_player or attribute_player:
                self._ignition_owner.setdefault(self.layer_key(), set()).add((x, y))
            if by_player:
                self._identity_ignition()
                self.emit_board_event('ignite', cell=(x,y), source_id=self.player.id,
                                      recipient_id='', amount=1)
            # 2026-10-15 混乱化改造：气爆半径按浓度三档（<50/1、<100/2、≥100/3），
            # 威力随心智失序档加成，低心智时连锁更狂暴。
            radius = 1 + min(2, concentration // 50)
            self.messages.append(tr("高浓度的气体轰然引爆！") + self._psyche_suffix())
            self._explode(x, y, radius, 2 + self.mind_tier, triggered=set(chain),
                          from_player=bool(by_player or attribute_player))
            if by_player:
                self._note_player_ignition()
            return True
        # 纵火者怀表（fire_affinity）：所有点燃来源的火焰强度 +1。
        strength += self._effect_power("fire_affinity")
        was_unlit = cell.flame <= 0
        self._set_flame(x, y, min(8, max(cell.flame, strength)))
        if by_player or attribute_player:
            self._ignition_owner.setdefault(self.layer_key(), set()).add((x, y))
        if by_player and was_unlit:
            self._identity_ignition()
            self.emit_board_event('ignite', cell=(x,y), source_id=self.player.id,
                                  recipient_id='', amount=1)
        self.run_stats["ignitions"] = self.run_stats.get("ignitions", 0) + 1
        if by_player:
            self._note_player_ignition()
        return True

    def _note_player_ignition(self) -> None:
        """灰烬撤步（ember_boots）：每层第一次亲手点燃 → 白得一步 + 近处追兵跟丢。

        「每次战斗限触发」按**每层一次**记账（下潜/回层即重新计时），与物品
        描述一致；点燃的连锁与蔓延不再传 by_player，所以烧一片也只撤一步。
        """
        if self._effect_power("ash_retreat") <= 0:
            return
        if self.bridge_once.get("ash_retreat") == self.depth:
            return
        self.bridge_once["ash_retreat"] = self.depth
        self.free_move_pending += 1
        lost = 0
        for enemy in list(self.enemies):
            if enemy.integrity <= 0 or enemy.alert_state != "追踪":
                continue
            if abs(enemy.x - self.player.x) + abs(enemy.y - self.player.y) > 3:
                continue
            # 与「失去视野 LOST_TARGET_TURNS 后降级」同一条口径（见 enemies）。
            enemy.alert_state = "怀疑"
            enemy.lost_sight_turns = 0.0
            enemy.wandering = True
            lost += 1
        self.messages.append(
            tr("靴跟的余烬散成灰：白得一步，{lost} 个追着你方向的失控意识跟丢了你。", lost=lost)
        )

    def _simulate_fire_burn_items(self) -> None:
        """每格每三回合烧掉一件可燃显化物，堆叠物逐件消耗。"""
        if not getattr(self, "_flame_cells", None):
            return
        burning = {(x, y) for x, y in self._flame_cells if self.cell(x, y).flame > 0}
        if not burning or not self.world_items:
            return
        from .content import item_is_flammable

        survivors: list = []
        burned: list = []
        progressed: set[tuple[int, int]] = set()
        for entry in self.world_items:
            if (entry.x, entry.y) in burning and item_is_flammable(entry.item):
                pos = (entry.x, entry.y)
                cell = self.cell(*pos)
                liquid = LIQUID_DEFINITIONS.get(cell.liquid_kind)
                extinguished = floor_fireproof(cell) or (cell.liquid >= 10 and
                    (cell.liquid_kind == "水" or (liquid and liquid.extinguishes_fire)))
                if extinguished:
                    survivors.append(entry)
                    continue
                if pos not in progressed:
                    cell.item_burn_progress += 1
                    progressed.add(pos)
                if cell.item_burn_progress >= 3:
                    cell.item_burn_progress = 0
                    if entry.item.quantity > 1:
                        entry.item.quantity -= 1
                        survivors.append(entry)
                    burned.append(entry)
                else:
                    survivors.append(entry)
            else:
                survivors.append(entry)
        if not burned:
            return
        self.world_items = survivors
        for entry in burned:
            cell = self.cell(entry.x, entry.y)
            self.messages.append(tr("{name}在火里烧尽了。", name=entry.item.name))
            # 烧起来的东西给本格续一点火（上限 8，与 _ignite_cell 同口径）。
            cell.flame = min(8, max(cell.flame, 3))
            if not cell.gas or cell.gas_kind == "黑烟":
                self._add_gas(cell, "黑烟", 8)
            self._sync_material_position(entry.x, entry.y)
        self._material_index_ready = False

    def _simulate_fire_damage(self, amount: int = 1) -> None:
        """站在火焰格上的意识体被灼：玩家清醒创伤 −1，实体完整度 −1。

        §6.1／§4.4：稳定意识（NPC）同样被灼——受灼立即向相邻安全格逃离
        （围死不动），玩家点的火烧到 TA 要归因（警告→同源再犯升级，relations
        读事实管道）；异象放的火、自然扩散不归因。异常死亡走环境击杀结算
        （视野外减半规则照旧）。
        """
        owner_cells = self._ignition_owner.get(self.layer_key(), set())
        for entity in [self.player, *self.enemies]:
            if entity is self.player and getattr(self,'stasis_turns',0)>0:
                continue
            if entity.integrity <= 0:
                continue
            cell = self.cell(entity.x, entity.y)
            if cell.flame <= 0:
                continue
            # 燃烧征兆（2026-09-19）：站在火焰格获得「燃烧」（4 回合），
            # 期间心智/清醒各 −1/回合；凤凰羽衣免疫灼伤但同样沾上征兆。
            if "burning" not in entity.portents and not (entity is self.player and self._identity_immune('burning')):
                self._apply_direct_portent(entity, "burning", 4)
            if entity is self.player:
                if self._effect_power("fire_ward") > 0:
                    continue  # 凤凰羽衣：火焰烧不着梦中的自己
                trauma = self._identity_environment_trauma(amount, 'fire')
                if (trauma > 0 and (entity.x, entity.y) in owner_cells):
                    from ..equipment.expansion_runtime import flame_guard
                    trauma = flame_guard(self, trauma)
                from .settlement import REASON_ENVIRONMENT, settle_delta
                settle_delta(
                    self, 'lucidity', -trauma,
                    reason=REASON_ENVIRONMENT, source='火焰')
                self.messages.append(tr("火焰舔过你的意识边缘（清醒 −1）。"))
            elif entity.relation == "稳定意识":
                damage = amount
                if (entity.x, entity.y) in owner_cells:
                    from ..equipment.expansion_runtime import owned_environment_bonus
                    damage += owned_environment_bonus(self, "owned_flame_damage", entity)
                self._npc_scorched(
                    entity, label="火", cause_uid="fire", damage=damage,
                    attributed=(entity.x, entity.y) in owner_cells)
            else:
                damage = amount
                if (entity.x, entity.y) in owner_cells:
                    from ..equipment.expansion_runtime import owned_environment_bonus
                    damage += owned_environment_bonus(self, "owned_flame_damage", entity)
                _damage_number_before = entity.integrity
                entity.integrity = max(0, entity.integrity - damage)
                from .hit_events import note_integrity_loss
                note_integrity_loss(self, entity, _damage_number_before)
                if entity.integrity <= 0:
                    self._resolve_enemy(entity)

    def _npc_scorched(self, entity: Entity, *, label: str, cause_uid: str,
                      damage: int, attributed: bool) -> None:
        """§6.1 最小行为态：被环境灼伤的稳定意识立刻逃离并（可归因时）记账。

        * 逃离在伤害之后——先挨这一下，再往相邻安全格挪一步（§6.1「受威胁
          逃离」的最小实现；岗位回归、呼救支援属后续批）。
        * harm 事实节流：连续被同源灼烧时每 4 世界回合至多记一条，免得一位
          站在火里的 NPC 把 240 条事实窗口灌掉一半；不可归因（异象火）不记
          ——relations 侧对 actor 非玩家的事实本来就跳过。
        * 死亡走既有环境击杀结算：remove 事实不归因（§4.4「事故致死不按
          已确认谋杀传播全派系追杀」，责任链由归因 harm 的警告/升级体现）。
        """
        from ..world import facts as world_facts
        from ..world import relations

        now = int(self.time)
        before = entity.integrity
        _damage_number_before = entity.integrity
        entity.integrity = max(0, entity.integrity - max(1, damage))
        from .hit_events import note_integrity_loss
        note_integrity_loss(self, entity, _damage_number_before)
        fled = self._flee_from_danger(entity)
        if attributed and before > entity.integrity:
            last = getattr(entity, "_last_harm_note", -10)
            if now - last >= 4:
                entity._last_harm_note = now
                world_facts.record(self, "harm", actor_uid=relations.player_uid(self),
                                   target_uid=entity.actor_uid or entity.id,
                                   position=(entity.x, entity.y), source_kind="environment",
                                   cause_uid=cause_uid, before=before,
                                   after=entity.integrity, amount=before - entity.integrity)
        if entity.integrity <= 0:
            self._resolve_enemy(entity)
            return
        if fled:
            last_note = getattr(entity, "_last_flee_note", -10)
            if now - last_note >= 8:
                entity._last_flee_note = now
                self.messages.append(tr("「{name}」被{label}燎到，慌忙躲开了。",
                                        name=tr(entity.label), label=label))

    def _flee_from_danger(self, entity: Entity) -> bool:
        """§6.1 逃离：向相邻最安全的格子挪一步（不寻路全图，一步足矣）。

        候选格：界内、非固体、无火焰、气体未达引爆浓度、无其他实体占据；
        取离原格最远的一格（斜角优先，更容易一步离开火心）。围死不动。
        挪完同步世界记录的账面坐标——行程投影（world.travel）按它落位。
        """
        best: tuple[int, int] | None = None
        best_key = -1
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = entity.x + dx, entity.y + dy
                if not (0 < nx < self.width - 1 and 0 < ny < self.height - 1):
                    continue
                target = self.cell(nx, ny)
                if target.solid or target.flame > 0:
                    continue
                if target.gas >= self.GAS_DETONATION_THRESHOLD:
                    continue
                occupant = self.entity_at(nx, ny)
                if occupant is not None and occupant is not entity:
                    continue
                key = max(abs(dx), abs(dy))
                if key > best_key:
                    best, best_key = (nx, ny), key
        if best is None:
            return False
        entity.x, entity.y = best
        record = self.world_ledger.actor(getattr(entity, "actor_uid", ""))
        if record is not None:
            record.x, record.y = best
        return True

    def _simulate_new_floors(self, amount: int = 1) -> None:
        """Excel 新一批地板的每回合结算（2026-09-18）：

        - 液氦：流经之处的火焰当场熄灭（无次生反应、不产蒸汽）；
        - 月壤：每 2 回合从本格气体中吸走 1 点；
        - 压电地板：上方生物每回合 +1 层蓄电，离开每回合 −1；攒满阈值放电，
          给 3×3 内的失控意识 2 点完整度创伤（2026-10-15 起玩家零创伤）；
        - 棋盘格地板：上方生物每回合 10% 随机获得一种常见增益征兆。
        """
        rng = random.Random(self.seed ^ (self.time * 0x9E3779B1))
        self._ensure_material_index()
        # 液氦灭火：液体索引里只查液氦格，便宜且与流动通道解耦。
        for x, y in tuple(self._liquid_cells):
            cell = self.cell(x, y)
            if cell.liquid_kind == "液氦" and cell.liquid > 0 and cell.flame:
                cell.flame = 0
        # 月壤吸气：气体索引里的月壤格每 2 回合吸 1 点。
        if self.time % 2 == 0:
            for x, y in tuple(self._gas_cells):
                cell = self.cell(x, y)
                effect = floor_effect_for(cell)
                if cell.gas > 0 and effect.gas_absorb > 0 and not effect.preserves_gas:
                    cell.gas = max(0, cell.gas - effect.gas_absorb)
        # 压电蓄电 / 棋盘格增益：按生物逐个结算（不扫全图）。
        stacks = getattr(self, "_piezo_stacks", None)
        if stacks is None:
            stacks = {}
            self._piezo_stacks = stacks
        occupants: dict[tuple[int, int], list] = {}
        for entity in [self.player, *self.enemies]:
            if entity.integrity > 0:
                occupants.setdefault((entity.x, entity.y), []).append(entity)
        for entity in [self.player, *self.enemies]:
            if entity.integrity <= 0:
                continue
            effect = floor_effect_for(self.cell(entity.x, entity.y))
            key = id(entity)
            if effect.piezo and (entity is self.player or entity.relation == "失控意识"):
                stacks[key] = stacks.get(key, 0) + amount
                # 蓄电征兆提示（2026-09-19）：层数实时可见，满 4 层放电后清零。
                # 放电结束后的保护窗口内电荷继续累积（环境照常），但征兆本身
                # 不得借此绕过保护重新出现。
                if self._apply_direct_portent(
                        entity, "charged_piezo", stacks[key], mode="set"):
                    entity.portent_stacks["charged_piezo"] = stacks[key]
                if stacks[key] >= effect.piezo_threshold:
                    stacks[key] = 0
                    # 保护窗口里征兆本就不存在，放电仍照环境规则结算，
                    # 但不能凭空记一次「结束」把保护期无限续下去。
                    if "charged_piezo" in entity.portents:
                        self._remember_portent_end(entity, "charged_piezo")
                    self._discharge_piezo(entity, occupants)
            else:
                remaining = stacks.get(key, 0)
                if remaining:
                    stacks[key] = max(0, remaining - amount)
            if effect.checkerboard and rng.random() < 1 - (1 - effect.buff_chance) ** amount:
                buff = rng.choice(CHECKER_BUFF_PORTENTS)
                definition = portent_def(buff)
                if definition is not None and entity.portents.get(buff, 0) <= 0:
                    self._apply_direct_portent(entity, buff, definition.duration or 8)
        # 灼热聚合物（2026-10-07，D1 放宽后允许）：站上每 3 回合清醒 −1，
        # ±1 量级、附可感知消息——不造成伤害、不改通行性。
        heat_ticks = self._rounds_crossed(self.time - amount, self.time, 3)
        if heat_ticks:
            player_floor = floor_effect_for(self.cell(self.player.x, self.player.y))
            if player_floor.scald_lucidity and self.lucidity > 0:
                from .settlement import REASON_ENVIRONMENT, settle_delta
                settle_delta(
                    self, 'lucidity', -player_floor.scald_lucidity * heat_ticks,
                    reason=REASON_ENVIRONMENT, source='灼热地板')
                self.messages.append(tr("灼热聚合物透过鞋底炙烤着意识：清醒度 −1。"))
            for enemy in self.enemies:
                if enemy.integrity > 0 and enemy.relation == "失控意识":
                    heat = floor_effect_for(self.cell(enemy.x, enemy.y)).scald_lucidity
                    if heat:
                        _damage_number_before = enemy.integrity
                        enemy.integrity = max(0, enemy.integrity - heat * heat_ticks)
                        from .hit_events import note_integrity_loss
                        note_integrity_loss(self, enemy, _damage_number_before)
                        if enemy.integrity == 0:
                            self._resolve_enemy(enemy)

    def shed_piezo_charge(self, entity, amount: int = 1) -> int:
        """验电时泄掉一格蓄电层（洞察「不把亮灯当通电」，2026-10-25）。

        只动 ``_piezo_stacks`` 这一本账：不拆地板、不提前恢复任何东西，也**不**走
        ``_remember_portent_end``——那会顺手开三回合保护窗，等于白送一层护身；而这里
        只是「身上这点电泄掉了」，压电地板下一回合照常继续充电（这就是「仍须实际
        断电，不因灯灭就安全」的结构实现）。返回这次真正泄掉的层数。
        """
        stacks = getattr(self, "_piezo_stacks", None)
        if not isinstance(stacks, dict):
            return 0
        key = id(entity)
        remaining = int(stacks.get(key, 0) or 0)
        if remaining <= 0:
            return 0
        taken = min(max(1, int(amount)), remaining)
        stacks[key] = remaining - taken
        if stacks[key] <= 0:
            stacks.pop(key, None)
            for book in (entity.portents, entity.portent_stacks, entity.portent_debt,
                         entity.portent_deadlines, entity.portent_attach):
                book.pop("charged_piezo", None)
        else:
            entity.portent_stacks["charged_piezo"] = stacks[key]
            # 征兆层数就是层数本身（同一本账，见 ``_simulate_new_floors``）；
            # 保护窗里征兆本就不在字典里，那时只改层数、不把征兆写回来。
            if "charged_piezo" in entity.portents:
                entity.portents["charged_piezo"] = stacks[key]
        return taken

    def _discharge_piezo(self, origin, occupants: dict) -> None:
        # 2026-09-19：触发后压电地板消失（退回普通聚合物）。
        cell = self.cell(origin.x, origin.y)
        if cell.aggregate_variant == "压电地板" and cell.floor is Material.PLAIN_AGGREGATE:
            cell.aggregate_variant = "普通聚合物"
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = origin.x + dx, origin.y + dy
                if 0 < nx < self.width - 1 and 0 < ny < self.height - 1:
                    neighbor = self.cell(nx, ny)
                    if neighbor.aggregate_variant == "压电地板" and neighbor.floor is Material.PLAIN_AGGREGATE:
                        neighbor.aggregate_variant = "普通聚合物"
        """压电地板放电：3×3 内的失控意识吃 2 点完整度创伤，稳定意识免疫，
        归零走正常崩解；玩家零创伤（2026-10-15 混乱化改造，地板零创伤回归）。"""
        ox, oy = origin.x, origin.y
        discharged = False
        struck: list = []
        for ty in range(oy - 1, oy + 2):
            for tx in range(ox - 1, ox + 2):
                for victim in occupants.get((tx, ty), ()):
                    if victim is not self.player and victim.relation != "失控意识":
                        continue
                    if victim is self.player:
                        # 2026-10-15 混乱化改造：地板零创伤回归——玩家站在放电
                        # 中心也只看个烟花，清醒度分毫不扣。
                        continue
                    # 2026-10-07：异象吃 2 点（对齐玩家侧清醒 −2 的量级）。
                    _damage_number_before = victim.integrity
                    victim.integrity = max(0, victim.integrity - 2)
                    from .hit_events import note_integrity_loss
                    note_integrity_loss(self, victim, _damage_number_before)
                    struck.append(victim)
                    if victim.integrity <= 0:
                        self._resolve_enemy(victim)
        if discharged:
            self.messages.append(tr("压电地板攒满了电荷，「啪」地放出一片电弧。"))
            # 潮润传导（浸盐的线圈）：玩家自己踩出来的那次放电，允许在
            # 湿润目标之间多传一次（2 格内、每 6 回合一次）。
            if (ox, oy) == (self.player.x, self.player.y):
                self._wet_conduct_chain(struck)

    def _simulate_special_materials(self) -> None:
        """内容扩展材料反应：火+水→灼热蒸汽；蜡化记忆墙热敏融解；
        《新材料》的烛泪柱/枕木/黄粱米堆燃烧转化与梦晶簇吸储气体。"""
        # 索引由写入处增量同步；只有墙体破坏等确实使索引失效的路径才重建，
        # 不再每拍无条件全图重建（docs §11 P0）。
        self._ensure_material_index()
        rng = random.Random(self.seed ^ (self.time * 2654435761))
        # 候选集：特殊墙体自身 + 火焰格 + 特殊墙体的相邻格
        # （燃烧看邻居火焰、吸储看邻居气体、热敏看邻居火焰）。
        candidates = set(self._special_cells) | set(self._flame_cells)
        for sx, sy in tuple(self._special_cells):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                candidates.add((sx + dx, sy + dy))
        # 超临界流体所在格也纳入候选（剥蚀相邻墙体）。
        for x, y in tuple(self._liquid_cells):
            if self.cell(x, y).liquid_kind == "超临界流体":
                candidates.add((x, y))
        for x, y in tuple(candidates):
            if not (0 < x < self.width - 1 and 0 < y < self.height - 1):
                continue
            cell = self.cell(x, y)
            neighbors = [
                (nx, ny)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                if 0 <= nx < self.width and 0 <= ny < self.height
            ]
            if cell.flame > 0:
                # 火+水→灼热蒸汽（30% 概率转化 10 点）。
                for nx, ny in neighbors:
                    neighbor = self.cell(nx, ny)
                    if not neighbor.solid and neighbor.liquid_kind == "水" and neighbor.liquid >= 10 and rng.random() < 0.3:
                        neighbor.liquid -= 10
                        if neighbor.liquid <= 0:
                            neighbor.liquid_kind = ""
                        self._add_gas(neighbor, "灼热蒸汽", 10, position=(nx, ny))
                        self._sync_material_position(nx, ny)
            if cell.liquid_kind == "超临界流体" and cell.liquid > 0:
                # 超临界流体渗进墙体缝隙：直接剥蚀相邻墙体（无需生物携带）。
                eroded = False
                for nx, ny in neighbors:
                    neighbor = self.cell(nx, ny)
                    if neighbor.solid and neighbor.wall_kind != "意识边界":
                        neighbor.integrity = max(0, neighbor.integrity - 3)
                        eroded = True
                        if neighbor.integrity == 0:
                            self.destroy_wall(nx, ny, "peel")
                if eroded:
                    # 事件消息每层只播一次（运行期记录，不进存档）。
                    notified = getattr(self, "_superfluid_notified_depths", None)
                    if notified is None:
                        notified = set()
                        self._superfluid_notified_depths = notified
                    if self.depth not in notified:
                        notified.add(self.depth)
                        self.messages.append(tr("超临界流体渗进墙体缝隙，石体簌簌剥落。"))
            if cell.solid and cell.wall_kind == "盐晶壁":
                # 盐晶壁遇水溶解：任一邻格有水即化。
                if any(self.cell(nx, ny).liquid_kind == "水" and self.cell(nx, ny).liquid > 0 for nx, ny in neighbors):
                    self.destroy_wall(x, y, "dissolve")
                    self.messages.append(tr("盐晶壁遇水，簌地溶掉了。"))
                    continue
            if cell.wall_kind in ("蜡化记忆墙", "烛泪柱", "枕木", "黄粱米堆"):
                if any(self.cell(nx, ny).flame > 0 for nx, ny in neighbors):
                    self._ignite_cell(x, y, 2)
                continue
            if cell.wall_kind in ("梦晶簇", "无意识结晶"):
                # 吸收 3×3 范围内全部气体并储存（不混合种类）。
                # 无意识结晶是深处的强化种：上限 160。
                capacity = (160 if cell.wall_kind == "无意识结晶" else 100) - cell.cover
                if capacity > 0:
                    for ny2 in range(max(1, y - 1), min(self.height - 1, y + 2)):
                        for nx2 in range(max(1, x - 1), min(self.width - 1, x + 2)):
                            if capacity <= 0:
                                break
                            neighbor = self.cell(nx2, ny2)
                            if neighbor.solid or neighbor.gas <= 0 or neighbor.gas_kind not in GAS_DEFINITIONS:
                                continue
                            if neighbor.wall_kind in CONTAINER_KINDS:
                                continue
                            if cell.cover > 0 and neighbor.gas_kind != cell.gas_kind:
                                continue
                            taken = min(capacity, neighbor.gas)
                            kind = neighbor.gas_kind
                            stored_key,decay_key = 'crystal_stored:' + kind,'crystal_decay:' + kind
                            stored = cell.material_clocks.get(stored_key,self.time)
                            previous_age = max(0,stored-cell.material_clocks.get(decay_key,stored)) if cell.cover else 0
                            source_age = max(0,self.time-neighbor.material_clocks.get('decay:' + kind,self.time))
                            cell.material_clocks[stored_key] = self.time
                            cell.material_clocks[decay_key] = self.time-max(previous_age,source_age)
                            if cell.cover == 0:
                                cell.gas_kind = neighbor.gas_kind
                            neighbor.gas -= taken
                            if neighbor.gas <= 0:
                                neighbor.gas_kind = ""
                            cell.cover += taken
                            capacity -= taken
                            self._sync_material_position(nx2,ny2)

    def _note_seen_reaction(self, recipe, x: int, y: int) -> None:
        """亲眼见过的液气反应记一笔（洞察「留意产物」的账）。

        只记**看得见**的格子：墙后自己响掉的反应不算「亲眼见过」，因此那条洞察也
        不会替你反演它。账按「反应物对＋产物」记（``reactions.reaction_key``），
        同一对材料换一格再看不会重复。
        """
        if not self.is_visible(x, y):
            return
        features = getattr(self, "realm_features", None)
        if not isinstance(features, dict):
            return
        from ..materials.reactions import reaction_key

        ledger = features.setdefault("seen_reactions", {})
        if not isinstance(ledger, dict):
            return
        ledger[reaction_key(recipe)] = int(self.time)
        if len(ledger) > 24:          # 只留最近见过的 24 条，旧档不会无限长
            for stale in sorted(ledger, key=lambda key: ledger[key])[:-24]:
                ledger.pop(stale, None)

    def _simulate_recipe_reactions(self) -> None:
        """液气反应与其他反应（墙/地板参与）的逐拍结算（materials/reactions.py）。

        混合类（液液/气气）在混合点（_mix_liquids / _resolve_material_arrivals）
        当场转化，不走这里；这里只管「液气同格全量转化」与逐拍推进的
        熔穿/崩解/脆裂/凝固/冻结。播报每种反应每层只播一次（运行期记录，
        不进存档），与超临界流体剥蚀的播报模式一致。
        """
        self._ensure_material_index()
        notified = getattr(self, "_recipe_notified_depths", None)
        if notified is None:
            notified = set()
            self._recipe_notified_depths = notified

        def notify(recipe: ReactionDef) -> None:
            if recipe.message and (self.depth, id(recipe)) not in notified:
                notified.add((self.depth, id(recipe)))
                self.messages.append(tr(recipe.message))

        for x, y in tuple(self._liquid_cells):
            if not (0 < x < self.width - 1 and 0 < y < self.height - 1):
                continue
            cell = self.cell(x, y)
            # ---- 液气反应：同格液气命中配方即全量转化（总量守恒、上限 100）----
            recipe = LIQUID_GAS_RECIPES.get(frozenset((cell.liquid_kind, cell.gas_kind)))
            if recipe and recipe.mechanism == 'lg_neutralize' and cell.liquid > 0 and cell.gas > 0:
                self._neutralize_hospital_dust(x, y)
                continue
            if cell.liquid >= 10 and cell.gas >= 10 and cell.gas_kind:
                recipe = LIQUID_GAS_RECIPES.get(frozenset((cell.liquid_kind, cell.gas_kind)))
                if recipe is not None:
                    if recipe.product_type == "液体":
                        cell.liquid_kind = recipe.product
                        cell.liquid = min(100, cell.liquid + cell.gas)
                        cell.gas, cell.gas_kind = 0, ""
                    else:  # 产物是气体：液量并入气量
                        cell.gas_kind = recipe.product
                        cell.gas = min(100, cell.gas + cell.liquid)
                        cell.liquid, cell.liquid_kind = 0, ""
                    self._sync_material_position(x, y)
                    self._note_seen_reaction(recipe, x, y)
                    notify(recipe)
                    continue
            # ---- 其他反应：液体格的邻接结算 ----
            neighbors = [
                (nx, ny)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                if 0 <= nx < self.width and 0 <= ny < self.height
            ]
            # 2026-09-19 性能改造：倒排索引只取与本格液体相关的配方
            # （通常 0–3 条），不再遍历整张 OTHER 表。
            for recipe in OTHER_BY_REACTANT.get(cell.liquid_kind, ()):
                mechanism = recipe.mechanism
                if mechanism == "wall_melt":
                    # 熔念金属渗进相邻固体墙：按配方扣完整度并消耗液体，熔穿后留一洼余浆。
                    if cell.liquid_kind == recipe.reactant_a and cell.liquid >= recipe.min_amount:
                        for nx, ny in neighbors:
                            neighbor = self.cell(nx, ny)
                            # 不腐蚀容器、机关、边界和可推解谜固体。
                            definition = WALL_DEFINITIONS.get(neighbor.wall_kind)
                            if (neighbor.solid and definition is not None and definition.hardness < 999
                                    and neighbor.wall_kind not in CONTAINER_KINDS and neighbor.wall_kind not in SOLID_KINDS
                                    and neighbor.wall_kind not in LOGIC_KINDS
                                    and not definition.path_clickable and not definition.pushable
                                    and not neighbor.wall_kind.startswith("逻辑")):
                                neighbor.integrity = max(0, neighbor.integrity - recipe.damage)
                                cell.liquid = max(0, cell.liquid - recipe.consumption)
                                if neighbor.integrity == 0:
                                    self.destroy_wall(nx, ny, "peel")
                                    self._add_liquid(self.cell(nx, ny), recipe.reactant_a, 5)
                                notify(recipe)
                                break
                elif mechanism == "wall_bust_gas":
                    # 酸蚀液剧烈溶蚀盐晶壁：墙崩解并放出毒气 20 点。
                    if cell.liquid_kind == recipe.reactant_b and cell.liquid > 0:
                        for nx, ny in neighbors:
                            neighbor = self.cell(nx, ny)
                            if neighbor.wall_kind == recipe.reactant_a:
                                self.destroy_wall(nx, ny, "dissolve")
                                self._add_gas(self.cell(nx, ny), recipe.product, 20)
                                notify(recipe)
                elif mechanism == "wall_shatter":
                    # 寒液脆裂墙体：每拍完整度 −8，消耗液体 1。
                    if cell.liquid_kind == recipe.reactant_b and cell.liquid >= recipe.min_amount:
                        for nx, ny in neighbors:
                            neighbor = self.cell(nx, ny)
                            if neighbor.wall_kind == recipe.reactant_a:
                                neighbor.integrity = max(0, neighbor.integrity - recipe.damage)
                                cell.liquid = max(0, cell.liquid - recipe.consumption)
                                if neighbor.integrity == 0:
                                    self.destroy_wall(nx, ny, "shatter")
                                notify(recipe)
                                break
                elif mechanism == "freeze_wall":
                    # 液态蜡与寒液相邻：当场凝固成蜡化记忆墙。
                    if cell.liquid_kind == recipe.reactant_a and cell.liquid > 0 and not cell.solid:
                        if any(
                            self.cell(nx, ny).liquid_kind == recipe.reactant_b and self.cell(nx, ny).liquid > 0
                            for nx, ny in neighbors
                        ):
                            cell.liquid, cell.liquid_kind = 0, ""
                            self.configure_wall(cell, recipe.product)
                            self._sync_material_position(x, y)
                            notify(recipe)
                elif mechanism == "freeze_floor":
                    # 水面与寒液相邻：整格冻成冰面（只覆盖普通聚合物地板，保留植物外的内容）。
                    if (
                        cell.liquid_kind == recipe.reactant_a and cell.liquid > 0
                        and not cell.solid and not cell.plant
                    ):
                        if any(
                            self.cell(nx, ny).liquid_kind == recipe.reactant_b and self.cell(nx, ny).liquid > 0
                            for nx, ny in neighbors
                        ):
                            cell.liquid, cell.liquid_kind = 0, ""
                            if cell.floor is Material.PLAIN_AGGREGATE:
                                cell.aggregate_variant = recipe.product
                            self._sync_material_position(x, y)
                            notify(recipe)
                elif mechanism == "wall_to_liquid":
                    # 墙化液：墙被相邻液体泡溶，整段墙消失、原地淌出产物液体。
                    if cell.liquid_kind == recipe.reactant_b and cell.liquid >= 10:
                        for nx, ny in neighbors:
                            neighbor = self.cell(nx, ny)
                            if neighbor.solid and neighbor.wall_kind == recipe.reactant_a:
                                self.destroy_wall(nx, ny, "dissolve")
                                self._add_liquid(self.cell(nx, ny), recipe.product, 20)
                                cell.liquid = max(0, cell.liquid - 10)
                                self._sync_material_position(x, y)
                                notify(recipe)
                                break
                elif mechanism == "wall_flush":
                    # 墙冲平：液体冲塌墙，原地留指定地板变体。
                    if cell.liquid_kind == recipe.reactant_b and cell.liquid >= 10:
                        for nx, ny in neighbors:
                            neighbor = self.cell(nx, ny)
                            if neighbor.solid and neighbor.wall_kind == recipe.reactant_a:
                                self.destroy_wall(nx, ny, "flush")
                                if neighbor.floor is Material.PLAIN_AGGREGATE:
                                    neighbor.aggregate_variant = recipe.product
                                cell.liquid = max(0, cell.liquid - 10)
                                self._sync_material_position(x, y)
                                notify(recipe)
                                break
                elif mechanism == "wall_retype":
                    # 墙改型：液体改写墙种（洗蜡/去锈/淬覆），墙还在、材料换了。
                    if cell.liquid_kind == recipe.reactant_b and cell.liquid >= 10:
                        for nx, ny in neighbors:
                            neighbor = self.cell(nx, ny)
                            if neighbor.solid and neighbor.wall_kind == recipe.reactant_a:
                                self.configure_wall(neighbor, recipe.product)
                                cell.liquid = max(0, cell.liquid - 10)
                                self._material_index_ready = False
                                notify(recipe)
                                break
                elif mechanism == "floor_revert":
                    # 地板退化：特殊地板浸入反应液体，退回指定地板变体（一般
                    # 是普通聚合物）。同格判定——液体就淌在这块地板上。
                    if (
                        not cell.solid and not cell.wall_kind
                        and cell.aggregate_variant == recipe.reactant_a
                        and cell.liquid_kind == recipe.reactant_b and cell.liquid >= 10
                    ):
                        cell.liquid = max(0, cell.liquid - 10)
                        if cell.liquid <= 0:
                            cell.liquid, cell.liquid_kind = 0, ""
                        if cell.floor is Material.PLAIN_AGGREGATE:
                            cell.aggregate_variant = recipe.product
                        notify(recipe)
                elif mechanism == "floor_pulp":
                    # 地板化液：特殊地板泡烂退回普通地面，并淌出产物液体。
                    # 媒介液体（reactant_b）被反应消耗：先清空再倒产物——否则
                    # 产物与本格残水混合，主导方判定会翻回媒介（如 水<纸浆 字典序）。
                    if (
                        not cell.solid and not cell.wall_kind
                        and cell.aggregate_variant == recipe.reactant_a
                        and cell.liquid_kind == recipe.reactant_b and cell.liquid >= 10
                    ):
                        cell.liquid, cell.liquid_kind = 0, ""
                        if cell.floor is Material.PLAIN_AGGREGATE:
                            cell.aggregate_variant = "普通聚合物"
                        self._add_liquid(cell, recipe.product, 20)
                        self._sync_material_position(x, y)
                        notify(recipe)
        # ---- 气体侧反应：气在墙上（低墙共存）与气蚀墙/气体地板退化 ----
        for x, y in tuple(self._gas_cells):
            if not (0 < x < self.width - 1 and 0 < y < self.height - 1):
                continue
            cell = self.cell(x, y)
            if cell.gas <= 0 or not cell.gas_kind:
                continue
            gas_neighbors = [
                (nx, ny)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                if 0 <= nx < self.width and 0 <= ny < self.height
            ]
            for recipe in OTHER_BY_REACTANT.get(cell.gas_kind, ()):
                mechanism = recipe.mechanism
                if mechanism == "wall_to_liquid":
                    # 热汽闷软低墙（高度 1 的墙允许气体共存）：墙化液。
                    if (
                        cell.gas_kind == recipe.reactant_b and cell.gas >= 15
                        and cell.solid and cell.wall_kind == recipe.reactant_a
                    ):
                        self.destroy_wall(x, y, "dissolve")
                        self._add_liquid(cell, recipe.product, 20)
                        cell.gas = max(0, cell.gas - 15)
                        if cell.gas <= 0:
                            cell.gas_kind = ""
                        self._sync_material_position(x, y)
                        notify(recipe)
                        break
                elif mechanism == "gas_etch":
                    # 酸雾蚀墙：气体与墙相邻，每拍完整度 −6，消耗气体 1，浓度至少 15。
                    if cell.gas_kind == recipe.reactant_a and cell.gas >= recipe.min_amount:
                        for nx, ny in gas_neighbors:
                            neighbor = self.cell(nx, ny)
                            if neighbor.solid and neighbor.wall_kind == recipe.reactant_b:
                                neighbor.integrity = max(0, neighbor.integrity - recipe.damage)
                                cell.gas = max(0, cell.gas - recipe.consumption)
                                if neighbor.integrity == 0:
                                    self.destroy_wall(nx, ny, "etch")
                                notify(recipe)
                                break
                elif mechanism == "floor_revert":
                    # 气体地板退化：反应气体笼罩特殊地板，退回普通地面。
                    if (
                        not cell.solid and not cell.wall_kind
                        and cell.aggregate_variant == recipe.reactant_a
                        and cell.gas_kind == recipe.reactant_b and cell.gas >= 15
                    ):
                        cell.gas = max(0, cell.gas - 15)
                        if cell.gas <= 0:
                            cell.gas_kind = ""
                        if cell.floor is Material.PLAIN_AGGREGATE:
                            cell.aggregate_variant = recipe.product
                        notify(recipe)

    @staticmethod
    def _flow_passable(cell: Cell) -> bool:
        """液体/气体的可通行格：开放格，以及可共存越过的低墙（高度 1）。"""
        return not cell.solid or cell.height <= 1

    @staticmethod
    def _gas_flow_passable(cell: Cell) -> bool:
        """Low walls allow gas above them; intact vessels remain sealed."""
        return MaterialSimMixin._flow_passable(cell) and cell.wall_kind not in CONTAINER_KINDS

    @staticmethod
    def _merge_material(existing_kind: str, existing: int, incoming_kind: str, incoming: int) -> tuple[str, int]:
        return MaterialSimMixin._resolve_material_arrivals(existing_kind, existing, [(incoming_kind, incoming)])

    @staticmethod
    def _resolve_material_arrivals(
        existing_kind: str,
        existing: int,
        arrivals: list[tuple[str, int]],
    ) -> tuple[str, int]:
        totals: dict[str, int] = {}
        if existing_kind and existing > 0:
            totals[existing_kind] = existing
        for kind, amount in arrivals:
            if kind and amount > 0:
                totals[kind] = totals.get(kind, 0) + amount
        if not totals:
            return "", 0
        # 气气反应配方（materials/reactions.py）在「强者通吃」之前结算：
        # 命中即整体转化为产物（全量转化、总量守恒、上限 100）。
        product = mix_pair(tuple(totals), GAS_GAS_PRODUCTS)
        if product:
            return product, min(100, sum(totals.values()))
        # 不稳定气体混合：起火（点燃态交给 flame 通道）或部分消失。
        if unstable_mix(tuple(totals)):
            rng = random.Random(MaterialSimMixin._unstable_seed(totals))
            if rng.random() < 0.5:
                winner, strongest = min(totals.items(), key=lambda entry: (-entry[1], entry[0]))
                return winner, min(100, strongest)
            return _UnstableExplosionResult(("黑烟", min(100, sum(totals.values()) * 3 // 10)))
        winner, strongest = min(totals.items(), key=lambda entry: (-entry[1], entry[0]))
        total_all = sum(totals.values())
        remaining = max(1, round(strongest * strongest / total_all)) if total_all > 0 else 0
        return (winner, min(100, remaining))

    # 水是「基底」液体：与另一种液体同格相遇时会被同化——按「对方量 /（对方量 + 水量）」
    # 的比例把水转成对方，然后重新取量最大的那种作为格子的显示类型。总量始终守恒
    # （相遇不再互相抵消体积），所以几回合接触下来水会被彻底同化，而不是原地互相磨掉。
    WATER_KIND = "水"

    @staticmethod
    def _mix_liquids(totals: dict[str, int]) -> tuple[str, int]:
        """把同格多种液体合并成 ``(种类, 总量)``：总量守恒，配方优先、水按比例被同化。

        转换量 = 总液量 × 对方量 /（对方量 + 水量）。水多时只被转走一小部分、
        本格仍显示水；对方多时本格当场翻成对方。多种非水液体同时存在时，
        取量最大者作为同化方向（与旧的「取主导方」同口径）。
        反应配方（materials/reactions.py）在同化之前结算：命中即整体转化为
        产物（全量转化、总量守恒、上限 100）。
        """
        totals = {kind: amount for kind, amount in totals.items() if kind and amount > 0}
        if not totals:
            return "", 0
        product = mix_pair(tuple(totals), LIQUID_LIQUID_PRODUCTS)
        if product:
            return product, min(100, sum(totals.values()))
        total = sum(totals.values())
        # 不稳定混合：无配方但含不稳定材料 → 起火或爆炸（同格归一仍保证单一种类）。
        # 纯查询将爆炸标记随结果返回，只由本次写入格子的入口执行爆炸。
        if unstable_mix(tuple(totals)):
            rng = random.Random(MaterialSimMixin._unstable_seed(totals))
            if rng.random() < 0.5:
                dominant, amount = min(totals.items(), key=lambda e: (-e[1], e[0]))
                return dominant, min(100, amount)
            return _UnstableExplosionResult(("黑烟", min(100, total * 3 // 10)))
        water = totals.get(MaterialSimMixin.WATER_KIND, 0)
        others = {
            kind: amount
            for kind, amount in totals.items()
            if kind != MaterialSimMixin.WATER_KIND
        }
        if water > 0 and others:
            other_kind, other_amount = min(others.items(), key=lambda entry: (-entry[1], entry[0]))
            converted = min(water, int(round(total * other_amount / (other_amount + water))))
            totals[MaterialSimMixin.WATER_KIND] = water - converted
            totals[other_kind] = other_amount + converted
            if totals[MaterialSimMixin.WATER_KIND] <= 0:
                del totals[MaterialSimMixin.WATER_KIND]
        dominant = min(totals.items(), key=lambda entry: (-entry[1], entry[0]))[0]
        return dominant, min(100, total)

    def _mark_unstable_explosion(self, cell) -> None:
        """不稳定混合爆炸：转真 _explode（半径 1、威力 2），保留本格火焰。"""
        cell.flame = max(cell.flame, 2)
        # Cell has no coordinates; use the owning grid rather than invented fields.
        for y, row in enumerate(self.cells):
            for x, candidate in enumerate(row):
                if candidate is cell:
                    self._explode(x, y, 1, 2)
                    return

    def _add_liquids(self, cell: Cell, totals: dict[str, int]) -> None:
        """批量液体入口：合并格子现有材料 + 全部到达材料 → 一次性归一 →
        完整执行本格爆炸 / 植物淹死 / 索引同步（与 _add_liquid 同口径）。"""
        if cell.liquid_kind and cell.liquid > 0:
            totals[cell.liquid_kind] = totals.get(cell.liquid_kind, 0) + cell.liquid
        result = self._mix_liquids(totals)
        cell.liquid_kind, cell.liquid = result
        self._prime_material_clocks(cell)
        if isinstance(result, _UnstableExplosionResult):
            self._mark_unstable_explosion(cell)
        if cell.liquid > 0 and cell.plant and not plant_survives_liquid(cell.plant):
            self.set_plant_at(cell, 0)
        self._material_index_ready = False

    def _add_gases(self, cell: Cell, arrivals: list[tuple[str, int]]) -> None:
        """批量气体入口。"""
        self._prime_material_clocks(cell)
        existing_kind = cell.gas_kind
        existing = cell.gas
        all_arrivals = list(arrivals)
        if existing_kind and existing > 0:
            all_arrivals.insert(0, (existing_kind, existing))
        totals: dict[str, int] = {}
        for kind, amount in all_arrivals:
            if kind and amount > 0:
                totals[kind] = totals.get(kind, 0) + amount
        if not totals:
            return
        # 用 _resolve_material_arrivals 一次性归一
        result = self._resolve_material_arrivals(
            "", 0, [(k, v) for k, v in totals.items()],
        )
        cell.gas_kind, cell.gas = result
        cell.gas = min(100, cell.gas)
        self._prime_material_clocks(cell)
        if isinstance(result, _UnstableExplosionResult):
            self._mark_unstable_explosion(cell)
        self._material_index_ready = False

    def _add_liquid(self, cell: Cell, kind: str, amount: int, *,
                    position: tuple[int, int] | None = None) -> None:
        totals: dict[str, int] = {}
        if cell.liquid_kind and cell.liquid > 0:
            totals[cell.liquid_kind] = cell.liquid
        if kind and amount > 0:
            totals[kind] = totals.get(kind, 0) + amount
        result = self._mix_liquids(totals)
        cell.liquid_kind, cell.liquid = result
        self._prime_material_clocks(cell)
        if isinstance(result, _UnstableExplosionResult):
            self._mark_unstable_explosion(cell)
        if cell.liquid > 0 and cell.plant and not plant_survives_liquid(cell.plant):
            # 液面漫过即淹死植物（容器破出、液体流动同为此通道）；蘑菇不受影响。
            self.set_plant_at(cell, 0)
        if position is not None:
            self._sync_material_position(*position, prime=False)
        else:
            self._material_index_ready = False

    def _remember_sealed_gas_age(self, item, kind: str, decay_mark: int) -> None:
        """Store elapsed phase, not a timestamp: portable contents pause in storage."""
        age = max(0, self.time-decay_mark)
        previous = item.gas_decay_age.get(kind, 0) if item.contents.get(kind, 0) > 0 else 0
        item.gas_decay_age[kind] = max(previous, age)

    def _add_gas(self, cell: Cell, kind: str, amount: int, *, decay_mark: int | None = None,
                 position: tuple[int, int] | None = None) -> None:
        self._prime_material_clocks(cell)
        existing_kind, existing_amount = cell.gas_kind, cell.gas
        result = self._resolve_material_arrivals(
            cell.gas_kind,
            cell.gas,
            [(kind, amount)],
        )
        cell.gas_kind, cell.gas = result
        cell.gas = min(100, cell.gas)
        if decay_mark is not None and amount > 0 and cell.gas > 0 and cell.gas_kind == kind:
            key = 'decay:' + kind
            previous = cell.material_clocks.get(key, self.time) if existing_kind == kind and existing_amount > 0 else self.time
            cell.material_clocks[key] = min(decay_mark, previous)
        self._prime_material_clocks(cell)
        if isinstance(result, _UnstableExplosionResult):
            self._mark_unstable_explosion(cell)
        if position is not None:
            self._sync_material_position(*position, prime=False)
        else:
            self._material_index_ready = False

    @staticmethod
    def _plan_material_transfers(
        x: int,
        y: int,
        targets: list[tuple[int, int]],
        amounts: dict[tuple[int, int], int],
        reserved: dict[tuple[int, int], int],
        budget: int,
        *,
        equalize: bool,
        use_kernel: bool,
    ) -> list[tuple[tuple[int, int], int]]:
        # use_kernel 由调用方在**每拍开始前**解析一次再传进来（2026-10-27）：
        # 本函数逐气体/液体源调用，单拍约 950 次；enabled() 每次都要读两个环境
        # 变量（实测 2.4µs/次 ≈ 2.3ms/行动），放在这里纯属重复付费。
        if use_kernel:
            return _kernel_plan_transfers(x, y, targets, amounts, reserved, budget, equalize)
        source_remaining = amounts.get((x, y), 0)
        target_levels = {
            target: amounts.get(target, 0) + reserved.get(target, 0)
            for target in targets
        }
        planned = {target: 0 for target in targets}
        while budget > 0 and source_remaining > 0:
            # 逐单位选「当前最低且仍可接收」的目标；不构造 candidates 列表，
            # 保持与旧实现完全相同的平局顺序（targets 顺序中的第一个最低）。
            chosen = None
            chosen_level = 0
            for target in targets:
                level = target_levels[target]
                if level >= 100:
                    continue
                if equalize and source_remaining - level < 2:
                    continue
                if chosen is None or level < chosen_level:
                    chosen = target
                    chosen_level = level
            if chosen is None:
                break
            target_levels[chosen] += 1
            source_remaining -= 1
            planned[chosen] += 1
            budget -= 1
        return [(target, planned[target]) for target in targets if planned[target] > 0]

    def _simulate_liquid_pass(self) -> None:
        self._ensure_material_index()
        # 只为有资格流动的液体源建立稀疏快照，避免每回合创建整张二维表。
        # 2026-09-19 性能改造：直接遍历液体活动格索引，不再全图扫描。
        sources: list[tuple[int, int, int, str]] = []
        amounts: dict[tuple[int, int], int] = {}
        candidates: list[tuple[int, int, int, str]] = list(
            getattr(self, "_deferred_liquid_sources", ()) or ()
        )
        height, width = self.height, self.width
        for x, y in tuple(self._liquid_cells):
            if not (0 <= y < height and 0 <= x < width):
                continue  # 陈旧索引坐标（换层竞态）：丢弃，50 回合校准会自愈
            cell = self.cells[y][x]
            if (
                cell.liquid >= LIQ_MIN_FLOW
                and cell.liquid_kind in LIQUID_DEFINITIONS
                and not (cell.solid and cell.height > 1)
                and cell.wall_kind not in CONTAINER_KINDS
            ):
                candidates.append((x, y, cell.liquid, cell.liquid_kind))
        # 每拍预算：超额部分连同当时的量快照一起延迟到下一拍处理。
        budget = self.SIM_SOURCE_BUDGET
        for x, y, amount, kind in candidates[:budget]:
            if not (0 < x < self.width - 1 and 0 < y < self.height - 1):
                continue  # 跨层残留坐标：丢弃
            sources.append((x, y, amount, kind))
            amounts[(x, y)] = amount
        self._deferred_liquid_sources = candidates[budget:]
        proposals: list[tuple[tuple[int, int], tuple[int, int], str, int]] = []
        reserved: dict[tuple[int, int], int] = {}
        from .expansion_abilities import liquid_pinned_cells
        pinned = liquid_pinned_cells(self)
        use_kernel = _kernel_enabled("gas")
        for x, y, amount, kind in sources:
                if (x,y) in pinned:
                    continue
                grid = self.cells
                source_cell = grid[y][x]
                definition = LIQUID_DEFINITIONS[kind]
                period = max(1, definition.flow_period)
                clock_key = "flow:" + kind
                if period > 1 and self.time - source_cell.material_clocks.get(clock_key, 0) < period:
                    continue
                neighbors = [
                    (nx, ny)
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                    if self._flow_passable(grid[ny][nx]) and grid[ny][nx].wall_kind != "云块"
                ]
                from ..equipment.remaining_gear import liquid_edge_allowed
                neighbors = [p for p in neighbors if liquid_edge_allowed(self,(x,y),p)]
                lower = [(nx, ny) for nx, ny in neighbors if grid[ny][nx].elevation < source_cell.elevation]
                if lower:
                    targets = lower
                else:
                    source_surface = source_cell.elevation * ELEV_STEP + amount
                    targets = [
                        (nx, ny)
                        for nx, ny in neighbors
                        if grid[ny][nx].elevation * ELEV_STEP + grid[ny][nx].liquid < source_surface
                    ]
                if not targets:
                    continue
                if period > 1:
                    source_cell.material_clocks[clock_key] = self.time
                rotation = (x + y + self.time) % len(targets)
                targets = targets[rotation:] + targets[:rotation]
                # 地板对流动预算的调节：光滑面加成、磨砂面打折。粗糙聚合物只是让
                # 扩散变慢，预算下限仍是 1，**不会**把液体堵死在原地。
                floor = floor_effect_for(source_cell)
                budget = definition.max_flow
                if floor.flow_bonus:
                    budget *= 1 + floor.flow_bonus
                if floor.flow_divisor > 1:
                    budget = max(1, budget // floor.flow_divisor)
                budget = min(amount, budget)
                equalize = not lower
                for target, transfer in self._plan_material_transfers(
                    x,
                    y,
                    targets,
                    amounts,
                    reserved,
                    budget,
                    equalize=equalize,
                    use_kernel=use_kernel,
                ):
                    proposals.append(((x, y), target, kind, transfer))
                    reserved[target] = reserved.get(target, 0) + transfer
        outgoing: dict[tuple[int, int], int] = {}
        incoming: dict[tuple[int, int], list[tuple[str, int]]] = {}
        for source, target, kind, transfer in proposals:
            outgoing[source] = outgoing.get(source, 0) + transfer
            incoming.setdefault(target, []).append((kind, transfer))
        touched = set(outgoing) | set(incoming)
        results = {
            position: (
                self.cell(*position).liquid_kind,
                max(0, self.cell(*position).liquid - outgoing.get(position, 0)),
            )
            for position in touched
        }
        for (x, y), arrivals in incoming.items():
            kind, amount = results[(x, y)]
            # 液体只会流动，不因不同液体相遇而凭空损失体积：保留总量，并按
            # 「水被其他液体同化」的规则重新定类型（见 _mix_liquids）。
            totals: dict[str, int] = {}
            if kind and amount > 0:
                totals[kind] = amount
            for incoming_kind, incoming_amount in arrivals:
                if incoming_kind and incoming_amount > 0:
                    totals[incoming_kind] = totals.get(incoming_kind, 0) + incoming_amount
            if totals:
                results[(x, y)] = self._mix_liquids(totals)
        for (x, y), (kind, amount) in results.items():
            cell = self.cell(x, y)
            cell.liquid_kind = kind if amount else ""
            cell.liquid = min(100, amount)
            if cell.liquid > 0 and cell.plant and not plant_survives_liquid(cell.plant):
                # 液体流进来的格子：植物被淹死（蘑菇扎根，液面漫过也不消失）。
                drowned_plant = self.set_plant(x, y, 0)
                if drowned_plant:
                    self._note_plant_wither(x, y, drowned_plant, "drowned")
            self._sync_material_position(x, y)

    def _apply_liquid_evaporation(self, instability: int) -> None:
        """液体挥发 + 地板吸水：两条损耗通道各按自己的周期结算。

        - **挥发**（``LiquidDef.evaporation`` + 地板 ``evaporation_bonus``）：
          旧材料与地板加成沿用 20 回合；特殊液体使用每格持久化的独立周期。
          特殊液体在气体容量不足时保留未转化液量，不补算离层时间。
        - **地板吸水**（``FloorDef.liquid_absorb``，海绵聚合物）：每
          ``LIQUID_ABSORB_INTERVAL``（2 回合）吸走 ``liquid_absorb`` 点，
          **不产气**——玩家举例的「海绵上的液体会慢慢消失」。周期刻意比挥发
          短得多，扣量也小，于是液体是被「一点点渗掉」而不是隔一阵突然少一截。

        两条通道分别用 ``liquid_decay_mark`` / ``liquid_absorb_mark`` 计时，
        互不牵制：海绵不必等满 20 回合，挥发节奏也不因为海绵而改变。

        原有通用液体的 ``evaporation`` 是 0，因此往常只有地板吸水这一路会耗掉
        液体：薄液膜先干、厚液池撑得久。液体相遇时不会互相抵消体积（守恒只
        针对流动），地板吸水与挥发是仅有的自然损耗通道。完整容器的内容物处于
        封存状态，不挥发也不被吸走。
        """
        del instability  # 损耗只按回合时间结算，不随失序档变化。
        evap_interval = LIQUID_DECAY_INTERVAL
        absorb_interval = LIQUID_ABSORB_INTERVAL
        evap_elapsed = self.time - self.liquid_decay_mark
        absorb_elapsed = self.time - self.liquid_absorb_mark
        evap_steps = evap_elapsed // evap_interval if evap_elapsed >= evap_interval else 0
        absorb_steps = absorb_elapsed // absorb_interval if absorb_elapsed >= absorb_interval else 0
        if evap_steps:
            self.liquid_decay_mark += evap_steps * evap_interval
        if absorb_steps:
            self.liquid_absorb_mark += absorb_steps * absorb_interval
        self._ensure_material_index()
        # 2026-09-19 性能改造：只扫有液体的格子（索引快照）。
        positions = self._liquid_cells if evap_steps or absorb_steps else self._periodic_liquid_cells
        for x, y in tuple(positions):
            cell = self.cells[y][x]
            changed = False
            if cell.liquid <= 0:
                continue
            if cell.wall_kind in CONTAINER_KINDS:
                # 容器完整时处于封存状态：内容物不挥发，也不被地板吸走。
                if "evap:" + cell.liquid_kind in cell.material_clocks:
                    cell.material_clocks["evap:" + cell.liquid_kind] = self.time
                continue
            definition = LIQUID_DEFINITIONS.get(cell.liquid_kind)
            floor = floor_effect_for(cell)

            def drain(amount: int, to_gas: bool) -> None:
                nonlocal changed
                if amount <= 0 or cell.liquid <= 0:
                    return
                liquid_kind = cell.liquid_kind
                taken = min(cell.liquid, amount)
                if to_gas and definition is not None and definition.evaporation_period > 0:
                    if definition.evaporation_gas not in GAS_DEFINITIONS:
                        return
                    ratio = max(1, definition.evaporation_ratio)
                    taken = min(taken, max(0, 100-cell.gas)//ratio)
                    if not taken:
                        return
                changed = True
                cell.liquid -= taken
                if cell.liquid <= 0:
                    cell.liquid = 0
                    cell.liquid_kind = ""
                if to_gas and definition is not None:
                    gas = definition.evaporation_gas
                    if gas and gas in GAS_DEFINITIONS:
                        self._add_gas(cell, gas, taken * max(1, definition.evaporation_ratio))
                        # 同格同回合只相变一次：蒸腾区读到这个标记就跳过本回合。
                        cell.material_clocks["phase:" + liquid_kind] = float(self.time)

            # 地板吸水：不产气的纯粹渗走（海绵聚合物），每 2 回合 1 点。
            if absorb_steps and floor.liquid_absorb:
                drain(absorb_steps * floor.liquid_absorb, to_gas=False)
            if cell.liquid <= 0 or definition is None:
                if changed:
                    self._sync_material_position(x, y)
                continue
            if definition.evaporation_period > 0:
                key = "evap:" + cell.liquid_kind
                period = definition.evaporation_period
                mark = cell.material_clocks.setdefault(key, self.time)
                steps = max(0, (self.time-mark)//period)
                if steps:
                    cell.material_clocks[key] = mark + steps*period
                    drain(steps * definition.evaporation, to_gas=True)
                # The floor's legacy heat bonus keeps its own global cadence.
                drain(evap_steps * floor.evaporation_bonus, to_gas=True)
            else:
                drain(evap_steps * (definition.evaporation + floor.evaporation_bonus), to_gas=True)
            if changed:
                self._sync_material_position(x, y)

    def _simulate_gas_pass(self) -> set[tuple[int, int]]:
        self._ensure_material_index()
        from .realm_challenges import sealed_gas_cells
        sealed = sealed_gas_cells(self)
        # 气体扩散同样使用稀疏快照；没有气体的地图不再分配两张整图数组。
        # 2026-09-19 性能改造：直接遍历气体活动格索引，不再全图扫描。
        sources: list[tuple[int, int, int, str]] = []
        amounts: dict[tuple[int, int], int] = {}
        # 开关在**每拍开头解析一次**再复用（2026-10-27 A4）：本函数原先在候选
        # 筛选与逐源转移两处各读一次 enabled()，而每次 enabled() 要读两个环境
        # 变量、且 gas pass 每动作会跑数拍。每次 pass 现读保证
        # ONEIRSCRIPT_CY_KERNEL_GAS 的运行时切换在下一拍立即生效（不做跨动作缓存）。
        use_kernel = _kernel_enabled("gas")
        if use_kernel:
            # CY-4：候选筛选的纯循环交给编译内核；顺序与预算完全一致。
            sources, amounts, deferred = _kernel_collect_gas_sources(
                self.cells, self.width, self.height, self._gas_cells,
                getattr(self, "_deferred_gas_sources", ()), sealed,
                self.SIM_SOURCE_BUDGET,
            )
            self._deferred_gas_sources = deferred
        else:
            candidates: list[tuple[int, int, int, str]] = list(
                getattr(self, "_deferred_gas_sources", ()) or ()
            )
            height, width = self.height, self.width
            for x, y in tuple(self._gas_cells):
                if not (0 <= y < height and 0 <= x < width):
                    continue  # 陈旧索引坐标：丢弃
                cell = self.cells[y][x]
                if (
                    cell.gas >= GAS_MIN_FLOW
                    and cell.gas_kind in GAS_DEFINITIONS
                    and not (cell.solid and cell.height > 1)
                    and cell.wall_kind not in CONTAINER_KINDS
                ):
                    candidates.append((x, y, cell.gas, cell.gas_kind))
            budget = self.SIM_SOURCE_BUDGET
            for x, y, amount, kind in candidates[:budget]:
                if (x, y) in sealed or not (0 < x < self.width - 1 and 0 < y < self.height - 1):
                    continue  # 跨层残留坐标：丢弃
                sources.append((x, y, amount, kind))
                amounts[(x, y)] = amount
            self._deferred_gas_sources = candidates[budget:]
        proposals: list[tuple[tuple[int, int], tuple[int, int], str, int]] = []
        reserved: dict[tuple[int, int], int] = {}
        from .expansion_abilities import liquid_pinned_cells
        pinned = liquid_pinned_cells(self)
        # use_kernel 已在本次 pass 开头解析（见上）。
        for x, y, amount, kind in sources:
                if (x,y) in pinned:
                    continue
                grid = self.cells
                source_cell = grid[y][x]
                targets = [
                    (nx, ny)
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                    if (nx, ny) not in sealed and self._gas_flow_passable(grid[ny][nx])
                    and grid[ny][nx].gas < amount
                ]
                if not targets:
                    continue
                rotation = (x + y + self.time) % len(targets)
                targets = targets[rotation:] + targets[:rotation]
                budget = min(amount, GAS_DEFINITIONS[kind].max_diffusion)
                liquid = LIQUID_DEFINITIONS.get(source_cell.liquid_kind)
                if liquid and source_cell.liquid >= liquid.gas_flow_threshold:
                    budget = max(1, budget // max(1, liquid.gas_flow_divisor))
                # 气泡藻（E11）：本格向四邻的扩散预算减半，对入流、自然消散与
                # 材料反应不加成——有益气体留得住，毒雾也留得住。
                divisor = plant_gas_flow_divisor(source_cell.plant)
                if divisor > 1:
                    budget = max(1, budget // divisor)
                for target, transfer in self._plan_material_transfers(
                    x,
                    y,
                    targets,
                    amounts,
                    reserved,
                    budget,
                    equalize=True,
                    use_kernel=use_kernel,
                ):
                    proposals.append(((x, y), target, kind, transfer))
                    reserved[target] = reserved.get(target, 0) + transfer
        outgoing: dict[tuple[int, int], int] = {}
        incoming: dict[tuple[int, int], list[tuple[str, int]]] = {}
        arrival_marks: dict[tuple[int, int], list[tuple[str, int]]] = {}
        for source, target, kind, transfer in proposals:
            outgoing[source] = outgoing.get(source, 0) + transfer
            incoming.setdefault(target, []).append((kind, transfer))
            mark = self.cell(*source).material_clocks.get('decay:' + kind, self.time)
            arrival_marks.setdefault(target, []).append((kind, mark))
        touched = set(outgoing) | set(incoming)
        results = {
            position: (
                self.cell(*position).gas_kind,
                max(0, self.cell(*position).gas - outgoing.get(position, 0)),
            )
            for position in touched
        }
        for position, arrivals in incoming.items():
            kind, amount = results[position]
            results[position] = self._resolve_material_arrivals(kind, amount, arrivals)
        exposed: set[tuple[int, int]] = set()
        # Snapshot clocks before touching cells: a source may also receive gas
        # in the same pass. New reaction products start now; surviving material
        # inherits its oldest participating clock, matching fan transport.
        result_marks = {}
        for position, (kind, amount) in results.items():
            old = self.cell(*position)
            marks = [mark for incoming_kind, mark in arrival_marks.get(position, ())
                     if incoming_kind == kind]
            if old.gas_kind == kind and old.gas-outgoing.get(position, 0) > 0:
                marks.append(old.material_clocks.get('decay:' + kind, self.time))
            result_marks[position] = min(marks, default=self.time)
        for (x, y), (kind, amount) in results.items():
            cell = self.cell(x, y)
            cell.gas_kind = kind if amount else ""
            cell.gas = min(100, amount)
            if cell.gas:
                cell.material_clocks['decay:' + kind] = result_marks[(x, y)]
            # 2026-09-19 性能改造：落点逐格增量同步进活动格索引（旧实现靠
            # 每拍全量重建掩盖了这里缺同步的问题）。
            self._sync_material_position(x, y)
            if cell.gas and 0 < x < self.width - 1 and 0 < y < self.height - 1 and any(
                not self.cell(nx, ny).solid
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            ):
                exposed.add((x, y))
        return exposed

    def _simulate_ventilation(self, amount: int = 1) -> None:
        """Move gas parcels once per world round, without mixing or discarding mass."""
        self._ensure_material_index()
        if not self._ventilation_cells:
            return
        for tick in range(max(0, self.time-max(0, amount)+1), self.time+1):
            self._ventilation_tick(tick)

    def _ventilation_tick(self, tick: int) -> None:
        for fx, fy in sorted(self._ventilation_cells):
            fan = self.cell(fx, fy)
            definition = wall_def(fan.wall_kind)
            if not fan.solid or not definition.gas_push_direction:
                continue
            if fan.material_clocks.get("fan", -1) >= tick:
                continue
            fan.material_clocks["fan"] = tick
            dx, dy = definition.gas_push_direction
            ray = []
            for distance in range(1, definition.gas_push_range+2):
                x, y = fx+distance*dx, fy+distance*dy
                if not (0 <= x < self.width and 0 <= y < self.height):
                    break
                if not self._gas_flow_passable(self.cell(x, y)):
                    break
                ray.append((x, y))
            # Farthest first: each original parcel advances exactly one cell.
            for i in range(len(ray)-2, -1, -1):
                source = self.cell(*ray[i])
                target = self.cell(*ray[i+1])
                if source.gas <= 0 or source.material_clocks.get("wind_moved", -1) >= tick:
                    continue
                if target.gas > 0 and target.gas_kind != source.gas_kind:
                    continue
                transfer = min(source.gas, max(0, 100-target.gas))
                if not transfer:
                    continue
                kind = source.gas_kind
                key = "decay:" + kind
                mark = source.material_clocks.get(key, self.time)
                if target.gas <= 0:
                    target.material_clocks[key] = mark
                else:
                    target.material_clocks[key] = min(mark, target.material_clocks.get(key, self.time))
                target.gas_kind, target.gas = kind, target.gas+transfer
                source.gas -= transfer
                if source.gas <= 0:
                    source.gas_kind = ""
                source.material_clocks["wind_moved"] = tick
                target.material_clocks["wind_moved"] = tick
                self._sync_material_position(*ray[i])
                self._sync_material_position(*ray[i+1])

    def _gas_decay_multiplier(self, x: int, y: int) -> int:
        if not self._exhaust_cells:
            return 1
        multiplier = 1
        for ny in range(max(0, y-1), min(self.height, y+2)):
            for nx in range(max(0, x-1), min(self.width, x+2)):
                if (nx, ny) not in self._exhaust_cells:
                    continue
                cell = self.cell(nx, ny)
                if cell.solid and cell.integrity > 0:
                    multiplier = max(multiplier, wall_def(cell.wall_kind).gas_dissipation_multiplier)
        return multiplier

    def _apply_gas_dissipation(self, exposed: set[tuple[int, int]], instability: int) -> None:
        """气体逐格按自身时钟消散，每周期扣类型定义的 dissipation 点数。

        扣减按格子结算，所以扩散摊薄本身就会加速整体稀薄化——气团先是变薄、
        再慢慢散尽，而不是停留一段时间后整片消失。完整容器的内容物处于封存
        状态，不参与消散。专属气体使用独立周期，密封地板跳过自然消散。
        """
        del exposed, instability  # 消散不再依赖暴露面或失序档，只按回合时间。
        interval = GAS_DECAY_INTERVAL + self.mind_tier * 2  # 心智失序：消散减慢（混乱化：每档 +2）
        elapsed = self.time - self.gas_decay_mark
        # Retained for legacy saves; actual decay is driven by per-cell clocks.
        steps = max(0, elapsed // interval)
        if steps:
            self.gas_decay_mark += steps * interval
        self._ensure_material_index()
        # 2026-09-19 性能改造：只扫有气体的格子（索引快照），逐格增量同步。
        # Each ordinary cloud has its own phase; a global tick cannot decide
        # which cells are due. The existing sparse index avoids a full-map scan.
        positions = self._gas_cells
        for x, y in tuple(positions):
            cell = self.cells[y][x]
            if cell.gas <= 0:
                continue
            definition = GAS_DEFINITIONS.get(cell.gas_kind)
            if definition is None:
                continue
            if cell.wall_kind in CONTAINER_KINDS:
                # 容器完整时处于封存状态：内容物不消散。
                cell.material_clocks["decay:" + cell.gas_kind] = self.time
                continue
            floor = floor_effect_for(cell)
            if floor.preserves_gas:
                cell.material_clocks["decay:" + cell.gas_kind] = self.time
                continue
            key = "decay:" + cell.gas_kind
            period = definition.dissipation_period or interval
            mark = cell.material_clocks.setdefault(key, self.time)
            cell_steps = max(0, (self.time-mark)//period)
            if not cell_steps:
                continue
            cell.material_clocks[key] = mark + cell_steps*period
            dissipation = max(1, definition.dissipation)
            if self.layer_modifier == "气密":
                # 气密层：气体更「耐存」——每降一浓度所需时间加倍（消散减半）。
                dissipation = max(1, dissipation // 2)
            # 灼热聚合物等：地板再补一点消散（余温把气团烘散）。
            dissipation += floor.gas_dissipation_bonus
            cell.gas = max(0, cell.gas - cell_steps * dissipation * self._gas_decay_multiplier(x, y))
            if not cell.gas:
                cell.gas_kind = ""
            self._sync_material_position(x, y)

    @staticmethod
    def _cell_is_flammable(cell: Cell, *, liquid_min: int = 1) -> bool:
        if plant_burns(cell.plant):
            return True
        wall = WALL_DEFINITIONS.get(cell.wall_kind)
        if wall and wall.flammable and cell.integrity > 0:
            return True
        liquid = LIQUID_DEFINITIONS.get(cell.liquid_kind)
        gas = GAS_DEFINITIONS.get(cell.gas_kind)
        from ..materials.floors import floor_effect_for
        if floor_effect_for(cell).burns_to:
            return True
        return bool((cell.liquid >= liquid_min and liquid and liquid.flammable) or (cell.gas > 0 and gas and gas.flammable))

    # ---- 植物枯萎/烧尽的视觉旁路（2026-10-26 Task 8）----------------------
    def _note_plant_wither(self, x: int, y: int, code: int, cause: str) -> None:
        """真实被烧尽/淹死的植株各登记一次枯萎事件（稳态采样不会重复）。"""
        if not code:
            return
        from .visual_events import emit_visual
        emit_visual(
            self, kind="plant.wither", outcome="hit", source=(int(x), int(y)),
            targets=((int(x), int(y)),), paths=(),
            affected_cells=((int(x), int(y)),),
            visual_key="plant.growth", tier=1, theme="plant",
            facts=(("plant", int(code)), ("cause", str(cause))),
            layer_key="plant",
        )
