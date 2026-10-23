"""异象主动技能 core 机制（2026-10-08，《梦层异象主动技能开发表》实装）。

数据层（dream_demo/data/anomaly_skills.py）提供 43 个技能定义、56 种异象绑定
与调参规则；本模块负责运行期机制：

- **起手 → 预警 → 结算**：``_enemy_active_skills()`` 每回合驱动。起手受
  CD（稳定技能 ID 记在 ``enemy.skill_clocks``）、共享起手间隔、初次警戒
  延迟、核心阶段解锁与并发预警上限约束；起手后进入蓄力（windup），预警格
  经 ``skill_telegraphs()`` 渲染静态警示底色（FX off 也可见）。
- **公平窗口**：创建 pending 时记录 ``warn_action_seq=self.action_seq``；
  只有 ``self.action_seq > warn_action_seq``（玩家至少又行动过一次）才允许
  倒计时/结算——同一玩家动作内创建的预警不得立刻结算。
- **双入口互斥**：蓄力/恢复中的异象 ``_enemy_can_strike()`` 返回 False，
  普攻入口（_charge_adjacent_attacks）与回合入口（_enemy_turns）都不得
  另结算；结算后本异象本动作不再行动。
- **名额公平调度**（§9，2026-10-22）：并发预警名额先到先得，
  ``slot_wait_since`` 记在技能状态里，放行者清零；相同起点按实体稳定
  标识排序，**与 ``self.enemies`` 的排列无关**（旧实现是列表前几只长期
  占先，见 ``core/skill_slots.py``）。
- **效果场**：``enemy_skill_fields`` 记录来源、寿命、实际格、渠道、每拍
  伤害与叠加族；同格同族取最大不叠加。场伤每回合 1 点、持续 2 拍（xlsx）。
- **召唤**：split_echo / core_summon 生成无奖励残影（寿命/完整度/单击/
  攻速按 xlsx，同源与全场预算按 TUNING），到期直接消散。
- **支援/治疗**：echo_alert 只广播最后目击位置；edit_heal 按遭遇预算
  （普通/强烈 20%、核心 10%，向下取整）且只治到完整度 ≤50%。

handler 用注册表分发（``_SKILL_CASTERS`` / ``_SKILL_RESOLVERS``），
不在 enemies.py 写 43 段 if。
"""

from __future__ import annotations

import math
from typing import Any

from ..data.anomaly_skills import (
    ANOMALY_SKILL_CONFIGS,
    SKILL_DEFINITIONS,
    TUNING,
    bindings_for,
    direct_damage,
    effective_skill_def,
)
from ..i18n import tr
from .cast_fx import animate_skill_resolution
from .entities import Entity
from .skill_slots import next_grants


# 减伤挡刀征兆（护折/护幕）挂在异象身上，玩家命中时消耗（见 _enemy_skill_guard_reduce）。
_GUARD_PORTENTS = ("sk_guard_fold", "sk_guard_choir")
# 软场（移动加值）：玩家踩进这类场时挂对应缠身征兆（可净化、离场不再续）。
_SLOW_FIELD_PORTENT = {
    "slow_frame": "sk_field_hamper",  # 迟帧光斑：+0.2
    "ink": "sk_field_hamper",         # 倾墨：+0.2
    "root": "sk_field_hamper",        # 盆中蔓延根丝：+0.2
    "frost": "sk_frost",              # 冻嚎寒痕：+0.3
}
# §8.1 声源盲投（2026-10-22，A8）：技能「明确允许对位置施放」的地面效果白名单。
# 看得见时照常以玩家实时格为心；失去视觉但有仍然有效的位置证据（最后目击点／
# 未过期调查任务／报信点）时投到证据格；没有证据就绝不起手，也不留实时追踪。
POSITION_CAST_FIELD_SKILLS = frozenset({
    "fog_veil", "slow_pool", "ink_pool", "nightmare_patch",
})
# 命中只结算预警格内的目标（这些技能没有独立 resolve，走默认结算）。
_DEFAULT_HIT_SKILLS = frozenset({
    "paper_dart", "light_trace", "mind_bite", "null_ray", "scribe_stroke",
    "model_push", "abyss_pull", "core_period", "core_beacon", "core_cry",
    "scribe_draft", "gift_bomb", "electric_stitch",
})
# §8.3 落空短记忆：同一技能最近两次因目标离开而扑空 → 下一次换手段。
_MISS_MEMORY_TURNS = 6
_MISSES_FOR_ADAPTATION = 2
_MISS_MEMORY_LIMIT = 6
# §8.1 有限预判：只给这些“锁定当前单格”的技能在连续落空后开放一格预判；
# 预判格仍写进本次预警，玩家停步或变向即可反制。不扩给其它技能。
ONE_CELL_PREDICTION_SKILLS = frozenset({
    "clock_drag", "seam_bind", "mislabel", "lullaby",
    "oblivion_mark", "core_pause",
})
# §8.3 换线：这些技能的命中沿细线推进，同伴站线上时既不穿人开火，
# 连续两次在同一格被同一方向躲开后也先换射击线。
RAY_SKILLS = frozenset({
    "paper_dart", "light_trace", "mind_bite", "null_ray", "scribe_stroke",
    "abyss_pull",
})
# §8.1 通路压制：这些「锚在玩家格的场」连续两次被玩家走出范围后，改压到
# 玩家已知活动区域的退路窄口；形状仍用既有范围几何，不新增技能。
SUPPRESSION_FIELD_SKILLS = frozenset({
    "slow_pool", "ink_pool", "nightmare_patch", "core_chill",
})
# 窄口判定：拿掉这格后，四周通路在小半径内接不上，才算门洞／一格宽走廊。
_CHOKE_MIN_OPENINGS = 2
_CHOKE_PROBE_RADIUS = 3
# 只在最近目击周围这么多步内找退路，不做全层搜索。
_SUPPRESSION_LOOKAHEAD = 4
# §9 相关遭遇范围：首轮用纯几何口径判定「这两只的预警算不算同一场遭遇」。
# 取现有技能最常见的射程量级（8 格），远处各自亮着的预警不再抢占本地名额。
ENCOUNTER_AREA_RADIUS = 8
# 整层同时亮起的预警仍有硬上限，避免按遭遇放开后全层无限铺开。
ENCOUNTER_TELEGRAPH_FLOOR_CEILING = 6


class EnemySkillMixin:
    """异象主动技能 Mixin：接入 GameState MRO（置于 EnemyMixin 之前）。"""

    # ------------------------------------------------------------------
    # 状态助手
    # ------------------------------------------------------------------

    def _skill_state(self, enemy: Entity) -> dict:
        """异象的主动技能运行期状态（pending/冷却记账/治疗预算/阶段）。"""
        state = getattr(enemy, "active_skill_state", None)
        if not isinstance(state, dict):
            state = {}
            enemy.active_skill_state = state
        return state

    def _uses_active_skills(self, enemy: Entity) -> bool:
        """该异象是否已由数据层绑定主动技能（存在 active_skill_bindings）。"""
        return not enemy.active_skill_state.get('summon_owner') and bool(bindings_for(getattr(enemy, "catalog_id", "")))

    def _skill_channeling(self, enemy: Entity) -> bool:
        """蓄力中或恢复中：本动作不得普攻/起手（双入口行动互斥的门槛）。"""
        if not self._uses_active_skills(enemy):
            return False
        st = self._skill_state(enemy)
        if st.get("pending") or st.get("library_second_beat"):
            return True
        if self.time < float(st.get("recover_until", 0)):
            return True
        return False

    def skill_cooldown_status(self, enemy: Entity) -> dict:
        """观察/观测显示用：该异象主动技能的运行时状态（2026-10-10）。

        各技能独立 CD（结算只写被施放技能的 clock）。「冷却剩余」按玩家
        的观察口径报告**最早何时会再起手**：全部绑定技能 clock 的最小正值，
        再与共享起手间隔余量（global_gap_rounds）、恢复硬直（recover_until）
        取大——这是下界：届时该技能的 caster 仍可能因条件不满足而放弃。
        蓄力中的技能单独报告。回合数一律向上取整（clock 是浮点、每回合
        如实递减）。返回：
        - 蓄力中：``{"charging": 技能id, "charging_name": 名, "windup_left": n}``
        - 等待中：``{"cooldown_left": n}``（n=最早 n 回合后才可能再起手）
        - 就绪：``{}``——调用方据此不写状态行。
        """
        if not self._uses_active_skills(enemy):
            return {}
        st = self._skill_state(enemy)
        pending = st.get("pending")
        if isinstance(pending, dict):
            skill_id = str(pending.get("skill_id", ""))
            skill = SKILL_DEFINITIONS.get(skill_id)
            windup = max(0.0, float(pending.get("windup_left", 0)))
            return {
                "charging": skill_id,
                "charging_name": skill.name_zh if skill is not None else skill_id,
                "windup_left": int(math.ceil(windup)),
            }
        clocks = [float(enemy.skill_clocks.get(binding.skill_id, 0))
                  for binding in bindings_for(getattr(enemy, "catalog_id", ""))]
        next_skill = min((clock for clock in clocks if clock > 0), default=0.0)
        config = ANOMALY_SKILL_CONFIGS.get(getattr(enemy, "catalog_id", ""))
        gap = int(config.global_gap_rounds) if config else 0
        gap_left = gap - (self.time - int(st.get("last_cast_start", -10**9)))
        recover_left = float(st.get("recover_until", 0)) - self.time
        remaining = max(next_skill, gap_left, recover_left, 0.0)
        return {"cooldown_left": int(math.ceil(remaining))} if remaining > 0 else {}

    def _player_control_immune(self) -> bool:
        """硬控制保护窗：被驻足/量尺位移后 4 回合内不再吃硬控制（不刷新）。"""
        until = (self.player.active_skill_state or {}).get("control_immune_until", 0)
        paid_until = self.player.active_skill_state.get("control_immune_paid_until", -1)
        return (self.time < float(until) or
                (self.difficulty_revision >= 3 and not self.realm_id
                 and self.paid_action_seq <= int(paid_until)))

    def _skill_grant_control_immunity(self) -> None:
        st = self.player.active_skill_state
        st["control_immune_until"] = self.time + int(TUNING["control_protection_rounds"])
        if self.difficulty_revision >= 3 and not self.realm_id:
            st["control_immune_paid_until"] = self.paid_action_seq + 1

    def _enemy_skill_guard_reduce(self, target: Entity) -> int:
        """护折/护幕：玩家命中异象时的减伤（−1，最低 1），命中即消耗。"""
        if not getattr(target, "active_skill_state", None) and not target.portents:
            return 0
        for pid in _GUARD_PORTENTS:
            if target.portents.get(pid, 0) > 0:
                self._remember_portent_end(target, pid)
                self.messages.append(tr("「{name}」挡下了这一击的部分创伤。", name=tr(pid)))
                return 1
        return 0

    def _enemy_skill_delay_windup(self, target: Entity) -> None:
        """抢拍（扩展包 v2，洞察）：命中蓄势中的异象 → 施法倒计时 +1 回合。

        只拖 pending 蓄势（公平窗口不动：warn_action_seq 保持原值，本动作内
        仍不会结算）；未蓄势的目标静默无感。"""
        st = getattr(target, "active_skill_state", None)
        pending = (st or {}).get("pending")
        if isinstance(pending, dict):
            pending["windup_left"] = float(pending.get("windup_left", 0)) + 1
            self.messages.append(tr(
                "你抢在它的节拍前面——「{skill}」的蓄势被拖慢了 1 回合。",
                skill=tr(SKILL_DEFINITIONS[pending["skill_id"]].name_zh),
            ))

    # ------------------------------------------------------------------
    # 伤害结算（与 _skill_trauma 同口径：护甲/镇静分级/忘忧减半/命中记账）
    # ------------------------------------------------------------------

    def _enemy_skill_trauma(self, enemy: Entity | None, power: int, channel: str, *, direct: bool = True) -> None:
        if getattr(self,'stasis_turns',0)>0:
            return
        if power <= 0 or channel == "无":
            return
        from .main_difficulty import effective_skill_power
        power = effective_skill_power(self, enemy, power)
        # 开局选项「异象强度」：技能创伤统一乘倍率（直接伤害与场伤同一口径）。
        power = max(0, round(power * self._enemy_trauma_mult()))
        trauma = power if channel == "心智" else 0
        lucidity_trauma = power if channel == "清醒" else 0
        # 2026-10-22：护甲减免后至少 1（未受伤的通道仍为 0），与贴身打击同口径。
        raw_trauma, raw_lucidity = trauma, lucidity_trauma
        trauma = max(0, trauma - self._effect_power("mind_armor") - self._effect_power("dual_armor"))
        lucidity_trauma = max(0, lucidity_trauma - self._effect_power("lucidity_armor") - self._effect_power("dual_armor"))
        if raw_trauma > 0:
            trauma = max(1, trauma)
        if raw_lucidity > 0:
            lucidity_trauma = max(1, lucidity_trauma)
        self._identity_direct_trauma(enemy, trauma, lucidity_trauma, direct=direct)
        if trauma or lucidity_trauma:
            self.run_stats["hits_taken"] = self.run_stats.get("hits_taken", 0) + 1
            if enemy is not None:
                self.last_harm_source = enemy.label
                self.last_harm_time = self.time

    def _skill_power(self, enemy: Entity, skill) -> int:
        """直接创伤：统一走数据层公式（层段倍率 + 阶级上限 + 绑定覆写）。"""
        layer = self.entry_depth if self.realm_id else self.depth
        return direct_damage(skill.skill_id, layer, enemy.catalog_id)

    # ------------------------------------------------------------------
    # 几何：预警格 / 锁定路径 / 目标格
    # ------------------------------------------------------------------

    def _sk_open(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height and not self.cell(x, y).solid

    def _sk_ray(self, x0: int, y0: int, x1: int, y1: int, max_len: int) -> list[tuple[int, int]]:
        """从 (x0,y0) 朝 (x1,y1) 的细线预警（不含起点）；高墙/遮挡格截断。"""
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        error = dx - dy
        x, y = x0, y0
        cells: list[tuple[int, int]] = []
        while (x, y) != (x1, y1) and len(cells) < max_len:
            doubled = 2 * error
            if doubled > -dy:
                error -= dy
                x += sx
            if doubled < dx:
                error += dx
                y += sy
            if not (0 <= x < self.width and 0 <= y < self.height):
                break
            cell = self.cell(x, y)
            if cell.solid and cell.wall_kind not in self._transparent_wall_kinds():
                break  # 不穿高墙、不跳弹
            cells.append((x, y))
        return cells

    @staticmethod
    def _transparent_wall_kinds() -> frozenset:
        from ..materials.walls import TRANSPARENT_WALLS

        return TRANSPARENT_WALLS

    def _sk_cross(self, cx: int, cy: int, radius: int) -> list[tuple[int, int]]:
        """固定十字（半径 1 = 5 格）。"""
        cells = [(cx, cy)]
        for step in range(1, radius + 1):
            cells.extend(((cx + step, cy), (cx - step, cy), (cx, cy + step), (cx, cy - step)))
        return [(x, y) for x, y in cells if 0 <= x < self.width and 0 <= y < self.height]

    def _sk_diamond(self, cx: int, cy: int, radius: int) -> list[tuple[int, int]]:
        """固定曼哈顿半径（r1 = 5 格，r2 = 13 格）。"""
        return [
            (x, y)
            for y in range(max(0, cy - radius), min(self.height, cy + radius + 1))
            for x in range(max(0, cx - radius), min(self.width, cx + radius + 1))
            if abs(x - cx) + abs(y - cy) <= radius
        ]

    def _sk_hline(self, cx: int, cy: int, toward_x: int, length: int) -> list[tuple[int, int]]:
        """固定短横线：以 (cx,cy) 为心朝目标方向的水平线。"""
        direction = 1 if toward_x >= cx else -1
        xs = range(cx, cx + length) if direction > 0 else range(cx, cx - length, -1)
        return [(x, cy) for x in xs if 0 <= x < self.width and 0 <= cy < self.height]

    def _sk_cone90(self, cx: int, cy: int, tx: int, ty: int, radius: int, max_cells: int) -> list[tuple[int, int]]:
        """固定 90° 扇形：朝目标的主方向 ±45°，切比雪夫半径内，取最近 max_cells 格。"""
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return []
        # 主方向量化为 8 向单位向量。
        length = max(abs(dx), abs(dy))
        ux, uy = round(dx / length), round(dy / length)
        cells: list[tuple[int, int]] = []
        for y in range(max(0, cy - radius), min(self.height, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(self.width, cx + radius + 1)):
                if (x, y) == (cx, cy) or self.cell(x, y).solid:
                    continue
                vx, vy = x - cx, y - cy
                if max(abs(vx), abs(vy)) > radius:
                    continue
                # 与主方向的夹角 ≤45°：两向量点积足够大（8 向格子的近似判定）。
                if vx * ux + vy * uy < max(abs(vx), abs(vy)) * 0.7:
                    continue
                cells.append((x, y))
        cells.sort(key=lambda c: (abs(c[0] - cx) + abs(c[1] - cy)))
        return cells[:max_cells]

    def _sk_player_line(self, enemy: Entity, skill) -> list[tuple[int, int]]:
        """弹道类技能的锁定射线：距离约束 + 视线 + 高墙截断。

        §4（2026-10-22 收口）：普通直射只消费「当前可见目标」或技能明确声明的独立感知；
        纯几何 Bresenham 不能代替 can_see——致盲与匿踪同样让射线失效。
        """
        if not self._sk_player_visible(enemy, skill.max_range):
            return []
        dist = max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y))
        if not (2 <= dist <= skill.max_range):
            return []
        if not self._has_line_of_sight(enemy.x, enemy.y, self.player.x, self.player.y):
            return []
        return self._sk_ray(enemy.x, enemy.y, self.player.x, self.player.y, skill.max_cells)

    def _sk_is_choke(self, x: int, y: int) -> bool:
        """窄口／门洞：拿掉这一格后，四周通路绕不回去。

        墙角不算（少掉它也能绕），开阔地不算（四面都接得上）；只承认一格宽的
        门与走廊，正是 §8.1 说的出口／退路。判定只做局部探测，不查整层连通性。
        """
        if not self._sk_open(x, y):
            return False
        openings = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if self._sk_open(x + dx, y + dy)]
        if len(openings) < _CHOKE_MIN_OPENINGS:
            return False
        reach = self._sk_local_reach(openings[0], blocked=(x, y))
        return any(cell not in reach for cell in openings[1:])

    def _sk_local_reach(self, start, blocked) -> set[tuple[int, int]]:
        """以 start 为心、跳过 blocked 格的有界 8 向连通集（半径 _CHOKE_PROBE_RADIUS）。"""
        seen = {start}
        frontier = [start]
        for depth in range(_CHOKE_PROBE_RADIUS):
            nxt = []
            for bx, by in frontier:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if (dx, dy) == (0, 0):
                            continue
                        cell = (bx + dx, by + dy)
                        if cell in seen or cell == blocked or not self._sk_open(*cell):
                            continue
                        seen.add(cell)
                        nxt.append(cell)
            frontier = nxt
        return seen

    def _suppression_anchor(self, enemy, skill, default):
        """§8.1 通路压制：连续两次被玩家走出范围后，把场压到退路窄口。

        候选只来自这异象现在看得见的地形与它自己的射程／视线，起点是玩家
        当前格（起手前提就是可见，等于最近目击）；向外逐圈找第一个合法窄口，
        找不到就退回原锚点，不为「聪明」制造新的合法目标。预警格与结算读
        同一份几何（§8.2）：换锚点只改中心，不延长范围。
        """
        if skill.skill_id not in SUPPRESSION_FIELD_SKILLS:
            return default
        if self._skill_whiff_penalty(enemy, skill.skill_id) != -1:
            return default
        origin = (self.player.x, self.player.y)
        seen = {origin}
        frontier = [origin]
        for _ in range(_SUPPRESSION_LOOKAHEAD):
            nxt = []
            for bx, by in frontier:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if (dx, dy) == (0, 0):
                            continue
                        cell = (bx + dx, by + dy)
                        if cell in seen or not self._sk_open(*cell):
                            continue
                        seen.add(cell)
                        if (self._sk_is_choke(*cell)
                                and self._suppression_cell_legal(enemy, skill, cell)):
                            # 换锚点的理由留在状态里，供 §11.3 的调试原因链读取。
                            self._skill_state(enemy)["suppression_anchor"] = {
                                "time": int(self.time), "skill_id": skill.skill_id,
                                "cell": list(cell),
                            }
                            return cell
                        nxt.append(cell)
            frontier = nxt
        return default

    def _suppression_cell_legal(self, enemy, skill, cell) -> bool:
        """压制的落点仍在本体合法射程与视线内，且不压在自己或同伴脚下。"""
        cx, cy = cell
        if max(abs(cx - enemy.x), abs(cy - enemy.y)) > int(skill.max_range):
            return False
        if not self._has_line_of_sight(enemy.x, enemy.y, cx, cy):
            return False
        occupant = self.entity_at(cx, cy)
        return occupant is None or occupant is enemy

    # ------------------------------------------------------------------
    # 起手 / 结算框架
    # ------------------------------------------------------------------

    def _one_cell_prediction(self, enemy, skill, warning_cells, target_cell):
        """§8.1 有限预判：连续两次落空后，把锁定格换成玩家续进的一格。

        只用于 ``ONE_CELL_PREDICTION_SKILLS`` 里的单格锁定技能；方向来自
        该异象最近两次真实目击，不读玩家未提交输入。预测格仍进入本次预警，
        玩家停步、变向或改变节奏即可反制；格子不合法就退回当前位置瞄准。
        """
        if skill.skill_id not in ONE_CELL_PREDICTION_SKILLS:
            return warning_cells, target_cell
        if not target_cell or not warning_cells or len(warning_cells) != 1:
            return warning_cells, target_cell
        current = (self.player.x, self.player.y)
        if tuple(target_cell) != current or tuple(warning_cells[0]) != current:
            return warning_cells, target_cell
        if self._skill_whiff_penalty(enemy, skill.skill_id) != -1:
            return warning_cells, target_cell
        qx, qy = enemy.last_seen_prev_x, enemy.last_seen_prev_y
        if qx < 0 or qy < 0:
            return warning_cells, target_cell
        dx = 0 if current[0] == qx else (1 if current[0] > qx else -1)
        dy = 0 if current[1] == qy else (1 if current[1] > qy else -1)
        if (dx, dy) == (0, 0):
            return warning_cells, target_cell
        nx, ny = current[0] + dx, current[1] + dy
        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return warning_cells, target_cell
        if self.cell(nx, ny).solid or self.entity_at(nx, ny) is not None:
            return warning_cells, target_cell
        if max(abs(nx - enemy.x), abs(ny - enemy.y)) > int(skill.max_range):
            return warning_cells, target_cell
        if not self._has_line_of_sight(enemy.x, enemy.y, nx, ny):
            return warning_cells, target_cell
        return [(nx, ny)], (nx, ny)

    def _skill_begin_cast(
        self,
        enemy: Entity,
        skill,
        warning_cells,
        locked_path=None,
        target_cell=None,
        meta: dict | None = None,
    ) -> None:
        warning_cells, target_cell = self._one_cell_prediction(
            enemy, skill, warning_cells, target_cell)
        st = self._skill_state(enemy)
        st["pending"] = {
            "skill_id": skill.skill_id,
            "windup_left": float(skill.windup_rounds),
            # 公平窗口：记录创建时的动作序号；同一玩家动作内不得倒计时/结算。
            "warn_action_seq": self.action_seq,
            "warning_cells": [[x, y] for x, y in (warning_cells or [])],
            "locked_path": [[x, y] for x, y in (locked_path or [])],
            "target_cell": list(target_cell) if target_cell else None,
            "meta": dict(meta or {}),
        }
        st["last_cast_start"] = self.time
        # §7.2 同价值轮换：记录每个技能上一次真正起手的时刻。
        st.setdefault("skill_last_used", {})[skill.skill_id] = int(self.time)
        # 蓄力预告只上顶部滚动（2026-10-12）：不进事件记录，这只播 3 秒。
        self.ticker_notes.append(tr(
            "{enemy}开始蓄势「{skill}」！",
            enemy=tr(enemy.label), skill=tr(skill.name_zh),
        ))

    def _enemy_skill_phase(self, enemy: Entity) -> int:
        """核心执念阶段（1–3）：按完整度三段划分；其余异象恒为 1。"""
        if enemy.anomaly_kind != "核心执念":
            return 1
        st = self._skill_state(enemy)
        maximum = st.get("max_integrity")
        if not maximum:
            from .content import ANOMALY_DEFINITIONS

            maximum = int(ANOMALY_DEFINITIONS.get(enemy.catalog_id, {}).get("integrity", enemy.integrity))
            st["max_integrity"] = max(1, maximum)
        maximum = max(1, int(maximum))
        from .content import ANOMALY_DEFINITIONS
        thresholds = ANOMALY_DEFINITIONS.get(enemy.catalog_id, {}).get('phase_thresholds') or (2/3, 1/3)
        if len(thresholds) == 1:
            phase = 1 if enemy.integrity > maximum * thresholds[0] else 2
        else:
            phase = 1 if enemy.integrity > maximum * thresholds[0] else 2 if enemy.integrity > maximum * thresholds[1] else 3
        if enemy.catalog_id == 'library.core' and st.get('library_phase', 1) != phase:
            st['library_phase'] = phase
            st.pop('pending', None)
            st['last_windup_end'] = ('broken', self.action_seq)
            st['recover_until'] = max(st.get('recover_until', 0), self.time + 1)
            self.realm_features.get('core', {})['phase'] = phase
            self.messages.append(tr('未尽目录翻到删改页；旧的索引预告被收回。'))
        if enemy.catalog_id == 'hospital.core_sterile_grace' and st.get('hospital_phase') != phase:
            st['hospital_phase'] = phase
            if phase == 3 and not st.get('pending'):
                st['recover_until'] = max(st.get('recover_until', 0), self.time+1)
                self.messages.append(tr('仍有变化，仍需净化。银白环停顿了一拍。'))
        if enemy.catalog_id == "anomaly.scribe":
            # 与旧终局旗标同步：书桌/结局路径仍读 scribe_phase。
            if self.epilogue_flags.get("scribe_phase") != phase:
                self.epilogue_flags["scribe_phase"] = phase
                from .epilogue import say

                self.messages.append(say("phase", phase=phase, name=say(f"phase{phase}")))
        return phase

    def _enemy_active_skills(self, enemy: Entity, amount: int) -> bool:
        """主动技能回合入口。返回 True 表示本次行动已被主动技能消耗。

        处理顺序：pending 倒计时/结算 → CD 递减 → 候选选择与起手。
        """
        bindings = bindings_for(getattr(enemy, "catalog_id", ""))
        if enemy.active_skill_state.get('summon_owner'):
            return False
        if not bindings:
            return False
        st = self._skill_state(enemy)
        if st.get('library_second_resolved_action') == self.action_seq:
            return True
        # 施法预算属于遭遇生命周期：在行动入口一次性建立，候选查询只读
        # （docs 261022 §7.1：caster 不再为比较候选反复写世界）。
        self._ensure_skill_budgets(enemy, bindings)
        # 阶段同步：即使起手门槛未满足（未察觉/初次警戒延迟），核心执念的
        # 阶段旗标也要随完整度刷新——终局书桌/结局路径仍读 scribe_phase。
        self._enemy_skill_phase(enemy)
        # CD：完成施放后记 max(CD, 恢复)，每回合如实递减。
        for binding in bindings:
            key = binding.skill_id
            clock = enemy.skill_clocks.get(key, 0)
            if clock > 0:
                enemy.skill_clocks[key] = max(0, clock - amount * self.hospital_cooldown_rate(enemy))
        # ---- pending 蓄力倒计时与结算（公平窗口门槛）----
        pending = st.get("pending")
        if isinstance(pending, dict):
            if self.action_seq > int(pending.get("warn_action_seq", -1)):
                pending["windup_left"] = float(pending.get("windup_left", 0)) - amount
                if pending["windup_left"] <= 0:
                    st.pop("pending", None)
                    st["last_windup_end"] = ("resolved", self.action_seq)
                    self._skill_resolve(enemy, pending)
                    skill = effective_skill_def(pending['skill_id'], enemy.catalog_id)
                    enemy.skill_clocks[skill.skill_id] = float(max(
                        skill.cooldown_rounds * self._run_mod('enemy_skill_cooldown', 1.0),
                        skill.recovery_rounds))
                    if skill.recovery_rounds > 0:
                        st["recover_until"] = self.time + skill.recovery_rounds
                    return True
            # 蓄力中：本回合只倒计时，不再普攻/移动。
            return True
        # ---- 恢复中：不起新手，但可移动 ----
        if self.time < float(st.get("recover_until", 0)):
            return False
        if not self._enemy_skill_may_start(enemy, bindings):
            return False
        # ---- 候选选择：先收集全部合法计划，再按收益与轮换决胜 ----
        # §7.2：槽位只是最后的稳定排序，不是永远第一的战术优先级。
        config = ANOMALY_SKILL_CONFIGS.get(enemy.catalog_id)
        gap = int(config.global_gap_rounds) if config else 0
        phase = self._enemy_skill_phase(enemy)
        candidates = bindings
        if enemy.catalog_id == 'hospital.core_sterile_grace' and phase >= 2:
            # Give the newly unlocked finite summon a chance before the always-
            # ready first ray slot; its budget and live-child limit still gate it.
            candidates = sorted(bindings, key=lambda b: b.skill_id != 'hospital.reopen')
        legal: list[tuple[int, int, object, object, tuple]] = []
        for index, binding in enumerate(candidates):
            if enemy.catalog_id == 'library.core' and phase == 2 and binding.skill_id in ('library.index_line', 'library.echo'):
                continue
            if st.get('library_second_beat'):
                return True
            if binding.phase > phase:
                continue
            skill = effective_skill_def(binding.skill_id, enemy.catalog_id)
            if enemy.skill_clocks.get(skill.skill_id, 0) > 0:
                continue
            if gap and self.time - int(st.get("last_cast_start", -10**9)) < gap:
                continue
            caster = self._SKILL_CASTERS.get(skill.skill_id)
            if caster is None:
                continue
            plan = caster(self, enemy, skill, binding)
            if plan is None:
                continue
            legal.append((self._skill_candidate_value(enemy, skill, binding), index,
                          skill, binding, plan))
        if not legal:
            return False
        # §9 名额公平调度：只有「真的有合法计划」的实体才进入等待队列，
        # 拿到名额者清零等待起点，其余记下起始动作序号继续等。
        if not self._skill_slot_allows(enemy):
            return False
        last_used = st.setdefault("skill_last_used", {})
        # 收益高者优先；同收益时选最久没用过的，最后按槽位稳定排序。
        legal.sort(key=lambda item: (-item[0], int(last_used.get(item[2].skill_id, -1)), item[1]))
        _, _, skill, binding, plan = legal[0]
        warning, locked, target, meta = plan
        # 无预警格的技能（自身征兆/召唤/治疗/支援）同样合法：
        # 条件判定已在 caster 内完成。
        self._skill_begin_cast(enemy, skill, warning or (), locked or (), target, meta)
        return True

    def _ensure_skill_budgets(self, enemy: Entity, bindings) -> None:
        """建立施法预算（当前只有 edit_heal 的遭遇治疗预算）。"""
        st = self._skill_state(enemy)
        if "heal_budget" in st or not any(b.skill_id == "edit_heal" for b in bindings):
            return
        from .content import ANOMALY_DEFINITIONS

        config = ANOMALY_SKILL_CONFIGS.get(enemy.catalog_id)
        maximum = int(ANOMALY_DEFINITIONS.get(enemy.catalog_id, {}).get("integrity", enemy.integrity))
        fraction = float(TUNING["heal_fraction_tier2"] if (config and config.tier == 2)
                         else TUNING["heal_fraction_tier01"])
        st["heal_budget"] = int(maximum * fraction)  # 向下取整

    def _skill_whiff_penalty(self, enemy: Entity, sid: str) -> int:
        """§8.3 短记忆：同一技能连续两次落空后，下一次优先换一种手段。

        只影响候选收益，不增加伤害、速度或感知；技能仍是唯一合法项时照常
        使用。记录本身也给 §11.3 的调试原因链提供事实。
        """
        misses = [
            m for m in self._skill_state(enemy).get("skill_misses", [])
            if m.get("skill_id") == sid and m.get("reason") == "target_left"
            and int(self.time) - int(m.get("time", 0)) <= _MISS_MEMORY_TURNS
        ]
        return -1 if len(misses) >= _MISSES_FOR_ADAPTATION else 0

    def _note_skill_miss(self, enemy: Entity, skill, reason: str = "target_left") -> None:
        self._skill_missed_this_resolution = True
        st = self._skill_state(enemy)
        misses = st.setdefault("skill_misses", [])
        # 记录开火格：§8.3 只有「在同一个位置」再次失手才需要换射击线；
        # 已经换过站位就不再反复横移。
        misses.append({"skill_id": skill.skill_id, "reason": reason,
                       "time": int(self.time), "x": enemy.x, "y": enemy.y})
        del misses[:-_MISS_MEMORY_LIMIT]

    def _recent_whiff_any(self, enemy: Entity) -> bool:
        """§8.3：这个位置最近是否已连续两次因目标离开落空。"""
        misses = [
            m for m in self._skill_state(enemy).get("skill_misses", [])
            if m.get("reason") == "target_left"
            and int(self.time) - int(m.get("time", 0)) <= _MISS_MEMORY_TURNS
        ]
        if len(misses) < _MISSES_FOR_ADAPTATION:
            return False
        return any((m.get("x"), m.get("y")) == (enemy.x, enemy.y)
                   for m in misses[-_MISSES_FOR_ADAPTATION:])

    def _clear_skill_misses(self, enemy: Entity, skill_id: str) -> None:
        st = self._skill_state(enemy)
        misses = [m for m in st.get("skill_misses", [])
                  if m.get("skill_id") != skill_id]
        if misses:
            st["skill_misses"] = misses
        else:
            st.pop("skill_misses", None)

    def _skill_candidate_value(self, enemy: Entity, skill, binding) -> int:
        """候选收益（§7.2）：只在「明显浪费／明显有效」时拉开差距。

        1 = 普通可用；0 = 合法但此刻重复（同伴已经知道当前位置）；
        2 = 有实际受益（治到真实受损同伴、告知未获情报的同伴、封住视线）；
        -1 = 同一技能最近连续落空，先换其他合法手段（§8.3）。
        默认值保持槽位顺序，避免为了轮换强放无效技能。
        """
        sid = skill.skill_id
        if sid == "echo_alert":
            allies = self._sk_allies_near(enemy, skill.max_range)[:2]
            point = self._echo_report_point(enemy)
            informed = [
                a for a in allies
                if a.alert_state == "追踪"
                and (a.last_seen_x, a.last_seen_y) == point
            ]
            if allies and len(informed) == len(allies):
                return 0
            return 2
        if sid in ("edit_heal", "wake_allies"):
            return 2
        if sid in ("fold_guard", "choir_guard"):
            # §7.2：无人接近时不为轮换续短盾；有真实威胁才值得起手。
            if sid == "fold_guard":
                threatened = (max(abs(enemy.x - self.player.x),
                                  abs(enemy.y - self.player.y)) <= 3
                              and self._enemy_sees_player(enemy))
            else:
                threatened = any(
                    max(abs(ally.x - self.player.x), abs(ally.y - self.player.y)) <= 3
                    and self._has_line_of_sight(ally.x, ally.y,
                                                self.player.x, self.player.y)
                    for ally in self._sk_allies_near(enemy, skill.max_range))
            return 2 if threatened else 0
        if sid == "fog_veil":
            distance = max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y))
            return 2 if distance >= 2 else 1
        penalty = self._skill_whiff_penalty(enemy, sid)
        return -1 if penalty else 1

    def _enemy_skill_may_start(self, enemy: Entity, bindings) -> bool:
        """起手门槛：初次警戒延迟 + 并发预警上限。"""
        st = self._skill_state(enemy)
        # 初次警戒延迟：从首次进入非「未察觉」状态算起。
        if enemy.alert_state == "未察觉":
            st.pop("alert_since", None)
            return False
        if "alert_since" not in st:
            st["alert_since"] = self.time
        config = ANOMALY_SKILL_CONFIGS.get(enemy.catalog_id)
        delay = int(config.initial_delay_rounds) if config else 0
        if self.time - int(st["alert_since"]) < delay:
            return False
        # §9 并发预警名额按相关遭遇范围调度：普通/强烈 2、核心房 3 的上限
        # 只数同一场遭遇里的 pending，远处无关的预警不再抢占本地名额；
        # 整层仍受一个硬上限约束，不会无限铺开。
        core_room = any(e.integrity > 0 and e.anomaly_kind == "核心执念" for e in self.enemies)
        limit = int(TUNING["concurrent_warning_limit_core_room"] if core_room
                    else TUNING["concurrent_warning_limit_ordinary"])
        if self.difficulty_revision >= 3 and not self.realm_id and self.depth <= 5:
            limit = min(limit, 1)
        related = 0
        floor_total = 0
        for other in self.enemies:
            if other is enemy or other.integrity <= 0:
                continue
            pending = self._skill_state(other).get("pending")
            if not pending:
                continue
            floor_total += 1
            if self._same_encounter(enemy, other, pending):
                related += 1
        return (related < limit
                and floor_total < max(limit, ENCOUNTER_TELEGRAPH_FLOOR_CEILING))

    def _same_encounter(self, enemy, other, other_pending) -> bool:
        """§9 相关遭遇范围：本体与已经亮起预警的同伴是否算同一场遭遇。

        首轮用可解释的几何口径：两只本体相距不超过 `ENCOUNTER_AREA_RADIUS`，
        或对方已预警／已锁定路径上的格子落在本体周围同半径内（相互影响的场
        与路径合并考虑）。这不是房间成员判定，也不承诺任何局面都有安全格。
        """
        if max(abs(other.x - enemy.x), abs(other.y - enemy.y)) <= ENCOUNTER_AREA_RADIUS:
            return True
        warned = list(other_pending.get("warning_cells") or [])
        warned += list(other_pending.get("locked_path") or [])
        for raw in warned:
            x, y = int(raw[0]), int(raw[1])
            if max(abs(x - enemy.x), abs(y - enemy.y)) <= ENCOUNTER_AREA_RADIUS:
                return True
        return False

    # ---- §9 名额公平调度（2026-10-22，A7 剩余项）----

    @staticmethod
    def _skill_slot_key(enemy: Entity) -> tuple:
        """等待队列里的实体标识：与 ``self.enemies`` 的排列无关。

        用「实体 id ＋ 目录 id ＋ 坐标」而不是列表下标——旧实现按列表顺序
        决定谁起手，列表前两只结算完立刻重新起手，后面的永远抢不到名额。
        """
        return (str(getattr(enemy, "id", "")), str(enemy.catalog_id),
                int(enemy.x), int(enemy.y))

    def _skill_slot_ready(self, enemy: Entity) -> bool:
        """「它在等名额」的廉价判据：不跑 caster、不写世界。

        只排除结构上不可能起手的情形（未察觉／蓄力中／恢复中／全技能 CD）。
        真正的合法性在候选收集后才确定；被本函数多算进来的一只没有等待
        起点（视作「刚就绪」），排在有等待记录的实体之后，不会把名额
        长期占死。
        """
        if enemy.integrity <= 0 or enemy.alert_state == "未察觉":
            return False
        st = self._skill_state(enemy)
        if st.get("pending"):
            return False
        if self.time < float(st.get("recover_until", 0)):
            return False
        bindings = bindings_for(getattr(enemy, "catalog_id", ""))
        if not bindings:
            return False
        return any(enemy.skill_clocks.get(b.skill_id, 0) <= 0 for b in bindings)

    def _skill_slot_wait(self, enemy: Entity) -> int:
        """等待起点（动作序号，越小等得越久）；没有记录＝刚刚就绪。"""
        st = self._skill_state(enemy)
        return int(st.get("slot_wait_since", self.action_seq))

    def _skill_slot_allows(self, enemy: Entity) -> bool:
        """本回合是否放行这只异象起手（§9 公平调度）。

        名额仍是遭遇级稀缺资源（普通／强烈 2、核心房 3，整层另有硬上限，
        由 ``_enemy_skill_may_start`` 先挡一层）。此处只决定**该轮到谁**：
        同遭遇里所有「在等」的实体按等待起点先到先得，起点相同按稳定标识
        排序，因此结果与实体列表顺序无关，也不会被同一批实体长期占据。
        """
        st = self._skill_state(enemy)
        own_key = self._skill_slot_key(enemy)
        # 已亮起的待结算预警仍占名额：可用名额 = 上限 − 同遭遇正在蓄力数。
        config = ANOMALY_SKILL_CONFIGS.get(enemy.catalog_id)
        core_room = any(e.integrity > 0 and e.anomaly_kind == "核心执念"
                        for e in self.enemies)
        limit = int(TUNING["concurrent_warning_limit_core_room"] if core_room
                    else TUNING["concurrent_warning_limit_ordinary"])
        if self.difficulty_revision >= 3 and not self.realm_id and self.depth <= 5:
            limit = min(limit, 1)
        related = sum(
            1 for other in self.enemies
            if other is not enemy and other.integrity > 0
            and self._skill_state(other).get("pending")
            and self._same_encounter(enemy, other, self._skill_state(other).get("pending") or {})
        )
        available = limit - related
        if available <= 0:
            st.setdefault("slot_wait_since", int(self.action_seq))
            return False
        competitors = [
            (self._skill_slot_key(other), self._skill_slot_wait(other))
            for other in self.enemies
            if other is not enemy and other.integrity > 0
            and self._same_encounter(enemy, other, {})
            and self._skill_slot_ready(other)
        ]
        competitors.append((own_key, self._skill_slot_wait(enemy)))
        if own_key in next_grants(competitors, available):
            st.pop("slot_wait_since", None)
            return True
        st.setdefault("slot_wait_since", int(self.action_seq))
        return False

    @animate_skill_resolution
    def _skill_resolve(self, enemy: Entity, pending: dict) -> None:
        skill_id = pending["skill_id"]
        skill = effective_skill_def(skill_id, enemy.catalog_id)
        resolver = self._SKILL_RESOLVERS.get(skill_id)
        self._skill_missed_this_resolution = False
        if resolver is not None:
            resolver(self, enemy, skill, pending)
        elif skill_id in _DEFAULT_HIT_SKILLS:
            self._skill_resolve_default_hit(enemy, skill, pending)
        else:
            # 无直接创伤也无专属结算的技能（支援/位移自身等）只发提示。
            self.messages.append(tr("「{skill}」的效果掠过了梦境。", skill=tr(skill.name_zh)))
        if not self._skill_missed_this_resolution:
            # 成功结算打断落空链：只有连续两次真的躲开才触发换手段。
            self._clear_skill_misses(enemy, skill_id)
            # §15 听觉通道：异象技能此前**一处也不发声**（全仓 acoustic 调用为 0），
            # 玩家的听觉线索只来自自己的动作与道具。技能真的落地了就按形状发一次声。
            self._emit_skill_sound(enemy, skill)

    # 形状 → 显示声径（§16.4 的 R 口径：正常源 Q = 2R）。自身类不出声——
    # 「卸掉重量」这种本来就是悄悄的；单格最轻，范围技最响。
    SKILL_SOUND_RADIUS = {
        "自身": 0,
        "固定单格": 2,
        "固定细线": 3, "固定短横线": 3, "固定十字": 3, "固定曼哈顿半径1": 3,
        "锁定局部范围": 4, "固定出生单格": 4,
    }

    def _skill_sound_radius(self, skill) -> int:
        shape = str(getattr(skill, "shape", "") or "")
        return int(EnemySkillMixin.SKILL_SOUND_RADIUS.get(shape, 2))

    def _emit_skill_sound(self, enemy: Entity, skill) -> None:
        """把一次成功施法记成真实声场（玩家听觉线索 + 可视化共用同一份）。

        刻意**不**让其他异象因此改道：异象之间互相听见、互相支援属于 AI 侧
        的另一条线（会改动一整批战术测试），本项只接「玩家能不能听见」。
        """
        radius = self._skill_sound_radius(skill)
        if radius <= 0:
            return
        pulse = getattr(self, "_sound_pulse", None)
        if pulse is None:
            return
        pulse(enemy.x, enemy.y, radius,
              category="skill", source=str(getattr(skill, "name_zh", "") or ""),
              announce=False, affect_enemies=False)

    def _skill_resolve_default_hit(self, enemy: Entity, skill, pending: dict) -> None:
        """默认结算：命中只发生在已预警格/路径内（跑出去就打不中）。"""
        warned = {tuple(c) for c in pending.get("warning_cells", [])}
        warned |= {tuple(c) for c in pending.get("locked_path", [])}
        capture = getattr(self, '_cast_fx_capture', None)
        if capture is not None:
            capture.resolved_path = tuple(tuple(c) for c in
                (pending.get('locked_path') or pending.get('warning_cells') or ()))
        if (self.player.x, self.player.y) not in warned:
            self.messages.append(tr("你避开了「{skill}」的范围。", skill=tr(skill.name_zh)))
            return
        power = self._skill_power(enemy, skill)
        self._enemy_skill_trauma(enemy, power, skill.trauma_channel)
        self.messages.append(tr(
            "{enemy}的「{skill}」命中了你（{channel} {power}）。",
            enemy=tr(enemy.label), skill=tr(skill.name_zh),
            channel=tr(skill.trauma_channel), power=power,
        ))
        self._skill_on_hit_extra(enemy, skill, pending)

    def _skill_on_hit_extra(self, enemy: Entity, skill, pending: dict) -> None:
        """命中附加（技能覆写驱动）：推移/拉拢/想象扣减/失焦等。"""
        meta = pending.get("meta") or {}
        overrides = meta.get("overrides") or {}
        if meta.get("push") and not self._player_control_immune():
            self._skill_push_player(enemy, away=True, safe=bool(overrides.get("push_to_safe_cell")))
        if meta.get("pull") and not self._player_control_immune():
            self._skill_push_player(enemy, away=False)
        if meta.get("imagination_hit"):
            from .settlement import REASON_COMBAT, settle_delta
            settle_delta(self, 'imagination', -int(meta["imagination_hit"]),
                         reason=REASON_COMBAT,
                         source=str(getattr(enemy, 'label', '异象主动技能')))
            self.messages.append(tr("这一击顺带抹去了你 {n} 笔想象力。", n=int(meta["imagination_hit"])))
        if meta.get("blur_on_hit"):
            self._grant_portent_direct(self.player, "sk_blur")
            self.messages.append(tr("视野像被贴错了标签——失焦了。"))

    def _skill_push_player(self, enemy: Entity, away: bool, safe: bool = False) -> None:
        """推移/拉拢 1 格：目的格被占或封死则不推动；不额外撞墙伤害。"""
        protected_main = self.difficulty_revision >= 3 and not self.realm_id
        if protected_main and self._player_control_immune():
            return
        dx = (self.player.x > enemy.x) - (self.player.x < enemy.x)
        dy = (self.player.y > enemy.y) - (self.player.y < enemy.y)
        if not away:
            dx, dy = -dx, -dy
        candidates = [(self.player.x + dx, self.player.y + dy)]
        if safe:
            # 教学覆写：推向安全格——优先无火、无场、无液体的邻格。
            candidates = [
                (nx, ny) for nx, ny in (
                    (self.player.x + dx, self.player.y + dy),
                    (self.player.x + dx, self.player.y),
                    (self.player.x, self.player.y + dy),
                    (self.player.x - dx, self.player.y),
                    (self.player.x, self.player.y - dy),
                )
                if (nx, ny) != (self.player.x, self.player.y)
            ]
        for nx, ny in candidates:
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue
            cell = self.cell(nx, ny)
            if cell.solid or self.entity_at(nx, ny) is not None:
                continue
            if safe and (cell.flame > 0 or cell.liquid > 0):
                continue
            self.player.x, self.player.y = nx, ny
            if protected_main:
                self._skill_grant_control_immunity()
            self.messages.append(tr("你被{verb}了 1 格！", verb=tr("推开") if away else tr("拉近")))
            self.trample_plant(nx, ny, self.player)
            return
        self.messages.append(tr("目的格被占住了——你纹丝没动。"))

    # ------------------------------------------------------------------
    # 效果场
    # ------------------------------------------------------------------

    def _sk_add_field(
        self,
        source: Entity,
        family: str,
        cells,
        channel: str = "无",
        rounds: int | None = None,
        tick_damage: int = 0,
        max_ticks: int = 0,
        damage_enemies: bool = False,
        note: str = "",
    ) -> None:
        """登记效果场：同来源同族先移除旧场；同格同族取最大（不叠加）。"""
        field_rounds = int(rounds if rounds is not None else TUNING["field_default_rounds"])
        new_cells = [
            [x, y] for x, y in cells
            if 0 <= x < self.width and 0 <= y < self.height and not self.cell(x, y).solid
        ]
        suppressed = self._sk_field_cells('library_blank')
        if family != 'library_blank':
            new_cells = [p for p in new_cells if tuple(p) not in suppressed]
        capture = getattr(self, '_cast_fx_capture', None)
        if capture is not None:
            if capture.resolved_area is None:
                capture.resolved_area = set()
            capture.resolved_area.update(tuple(p) for p in new_cells)
        if not new_cells:
            return
        fields = [
            f for f in self.enemy_skill_fields
            if not (f.get("source_id") == source.id and f.get("family") == family)
        ]
        # 同格同族取最大：新场每格回合数更高才覆盖旧场该格。
        for field in fields:
            if field.get("family") != family:
                continue
            kept = []
            for cell in field.get("cells", []):
                key = (cell[0], cell[1])
                if key in {(c[0], c[1]) for c in new_cells} and field_rounds >= field.get("rounds_left", 0):
                    continue  # 新场更强（或相等）：旧场该格让位
                kept.append(cell)
            field["cells"] = kept
        fields = [f for f in fields if f.get("cells")]
        fields.append({
            "source_id": source.id,
            "family": family,
            "cells": new_cells,
            "channel": channel,
            "rounds_left": field_rounds,
            "tick_damage": int(tick_damage),
            "max_ticks": int(max_ticks),
            "ticks_done": 0,
            "damage_enemies": bool(damage_enemies),
            "note": note,
        })
        self.enemy_skill_fields = fields

    def _sk_field_cells(self, family: str = "") -> set[tuple[int, int]]:
        cells: set[tuple[int, int]] = set()
        for field in self.enemy_skill_fields:
            if family and field.get("family") != family:
                continue
            cells |= {(c[0], c[1]) for c in field.get("cells", [])}
        return cells

    def _enemy_skill_fields_tick(self, amount: int) -> None:
        """效果场与召唤寿命的逐回合结算（在 _enemy_turns 主循环前调用一次）。"""
        from .library_skills import tick as tick_library_skills
        from .realm_enrichment import tick_scavenge
        tick_scavenge(self)
        tick_library_skills(self, amount)
        from .hospital_skills import tick_light_pulses
        tick_light_pulses(self, amount)
        # ---- 召唤寿命：到期直接消散（无奖励、不进 _resolve_enemy）----
        for enemy in list(self.enemies):
            expire = (enemy.active_skill_state or {}).get("summon_expire")
            if expire is not None and enemy.integrity > 0 and self.time >= float(expire):
                enemy.integrity = 0
                self.enemies.remove(enemy)
                self.messages.append(tr("{label}的残影散成了纸屑。", label=tr(enemy.label)))
        if not self.enemy_skill_fields and "sk_faded_ink" not in self.portents:
            return
        # ---- 淡墨：每回合想象力 −1（共 2 点，不按深度放大；净化即停）----
        if self.portents.get("sk_faded_ink", 0) > 0:
            drained = min(amount, 2, self.imagination)
            if drained > 0:
                from .settlement import REASON_COMBAT, settle_delta
                settle_delta(self, 'imagination', -drained, reason=REASON_COMBAT,
                             source='遗忘的批注')
                self.messages.append(tr("遗忘的批注又淡了一分：想象力 −{n}。", n=drained))
        player_pos = (self.player.x, self.player.y)
        survivors: list[dict] = []
        for field in self.enemy_skill_fields:
            family = field.get("family", "")
            if family == "tamper_fire_preview":
                # 页边余火的预警族：不按回合倒计时，只由「玩家下一次耗时行动」
                # 收尾（core/tamper_previews.resolve_tamper_previews）。
                survivors.append(field)
                continue
            cells = [(c[0], c[1]) for c in field.get("cells", [])]
            # 根丝可被烧掉；折面/薄雾不挡火。
            if family == "root":
                cells = [c for c in cells if self.cell(c[0], c[1]).flame <= 0]
                field["cells"] = [[x, y] for x, y in cells]
            # 每回合 1 拍伤害（持续 max_ticks 拍口径按 xlsx）。
            tick_damage = int(field.get("tick_damage", 0))
            max_ticks = int(field.get("max_ticks", 0))
            ticks = 0
            if tick_damage > 0 and (max_ticks <= 0 or int(field.get("ticks_done", 0)) < max_ticks):
                ticks = min(amount, max_ticks - int(field.get("ticks_done", 0)) if max_ticks else amount)
                if player_pos in cells:
                    self._enemy_skill_field_damage(field, tick_damage)
                if field.get("damage_enemies"):
                    for enemy in self.enemies:
                        if enemy.integrity > 0 and (enemy.x, enemy.y) in cells:
                            enemy.integrity = max(0, enemy.integrity - tick_damage)
                            if enemy.integrity <= 0:
                                self._resolve_enemy(enemy)
            field["ticks_done"] = int(field.get("ticks_done", 0)) + max(0, ticks)
            field["rounds_left"] = int(field.get("rounds_left", 0)) - amount
            # 慢场：玩家踩在里面挂上缠身征兆（可净化；离场不再续）。
            slow_portent = _SLOW_FIELD_PORTENT.get(family)
            if slow_portent and player_pos in cells and getattr(self,'stasis_turns',0)<=0:
                self._apply_direct_portent(self.player, slow_portent, 2)
            if field["rounds_left"] > 0 and field["cells"]:
                survivors.append(field)
                continue
            # 场到期：火场收尾熄灭余火，其余场直接消散。
            # （同族同格在登记时已去重，不存在别的 ember 场覆盖这些格。）
            if family == "ember":
                for x, y in cells:
                    self.cell(x, y).flame = 0
            if field.get("note"):
                self.messages.append(tr(field["note"]))
        self.enemy_skill_fields = survivors

    def _enemy_skill_field_damage(self, field: dict, power: int) -> None:
        channel = field.get("channel", "无")
        source = next(
            (e for e in self.enemies if e.id == field.get("source_id")),
            None,
        )
        self._enemy_skill_trauma(source, power, channel, direct=False)
        self.messages.append(tr(
            "效果场灼着你：{channel} −{power}。",
            channel=tr(channel), power=power,
        ))

    # ------------------------------------------------------------------
    # 预警渲染（FX off 也必须能看到：静态警示底色，见 ui/render.py）
    # ------------------------------------------------------------------

    def skill_telegraphs(self) -> dict[tuple[int, int], str]:
        tele = super().skill_telegraphs()  # type: ignore[misc]
        for enemy in self.enemies:
            if enemy.integrity <= 0:
                continue
            for p in self._skill_state(enemy).get('library_second_beat', {}).get('cells', ()):
                tele[tuple(p)] = 'cast'
            pending = self._skill_state(enemy).get("pending")
            if not isinstance(pending, dict):
                continue
            for x, y in pending.get("warning_cells", []):
                tele[(x, y)] = "cast"
            for x, y in pending.get("locked_path", []):
                tele.setdefault((x, y), "cast_path")
        for field in self.enemy_skill_fields:
            for x, y in field.get("cells", []):
                tele.setdefault((x, y), "field")
        return tele

    def _skill_sight_blockers(self) -> set[tuple[int, int]]:
        """阻断远程视线与弹道的临时格（薄雾/折面场）： SightMixin 的
        ``_has_line_of_sight`` 在逐格判定里读这里（它在 MRO 中先于本
        Mixin，覆盖写法会被遮蔽，故走这个挂钩）。"""
        return self._sk_field_cells("fog") | self._sk_field_cells("fold")

    # ------------------------------------------------------------------
    # 召唤 / 支援 / 治疗
    # ------------------------------------------------------------------

    def _sk_summon_alive(self, source_id: str) -> int:
        return sum(
            1 for e in self.enemies
            if e.integrity > 0 and e.trait == "phantom" and e.main_id == source_id
            and (e.active_skill_state or {}).get("summon_expire") is not None
        )

    def _sk_summon_spots(self, enemy: Entity) -> list[tuple[int, int]]:
        """§9 召唤落点：不堵住施法者自己的出口或通往目标的通道。

        优先避开施法者下一步要走的位置、唯一可用的相邻出口，以及通往
        最近目标方向上仅剩的出口；没有安全落点时返回空表（宁可召唤失败，
        也不把己方困在墙角）。
        """
        next_step = None
        if enemy.path_plan and enemy.plan_index < len(enemy.path_plan):
            next_step = tuple(enemy.path_plan[enemy.plan_index])
        open_neighbors = [
            (enemy.x + dx, enemy.y + dy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 < enemy.x + dx < self.width - 1 and 0 < enemy.y + dy < self.height - 1
            and not self.cell(enemy.x + dx, enemy.y + dy).solid
            and self.entity_at(enemy.x + dx, enemy.y + dy) is None
        ]
        tx, ty = enemy.last_seen_x, enemy.last_seen_y
        if tx >= 0 and ty >= 0:
            here = max(abs(enemy.x - tx), abs(enemy.y - ty))
            forward = [p for p in open_neighbors
                       if max(abs(p[0] - tx), abs(p[1] - ty)) < here]
        else:
            forward = []
        spots = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (-1, -1), (1, -1), (-1, 1)):
            x, y = enemy.x + dx, enemy.y + dy
            if not (0 < x < self.width - 1 and 0 < y < self.height - 1):
                continue
            if self.cell(x, y).solid or self.entity_at(x, y) is not None:
                continue
            if next_step is not None and (x, y) == next_step:
                continue
            if len(open_neighbors) <= 1 and (x, y) in open_neighbors:
                continue
            if (x, y) in forward and len(forward) < len(open_neighbors):
                continue
            spots.append((x, y))
        return spots

    def _sk_spawn_summon(self, enemy: Entity, integrity: int, life: int, attack_time: float, variant: str = "") -> None:
        label = "残影"
        spots = self._sk_summon_spots(enemy)
        if not spots:
            self.messages.append(tr("{enemy}想唤出残影，却找不到落脚处。", enemy=tr(enemy.label)))
            return
        for x, y in spots:
            summon = self.add_enemy(
                label, x, y,
                integrity=integrity, move_time=1.5, attack_time=attack_time,
                trauma_type=enemy.trauma_type, communicates=False,
                drop_id=None, dissolution_reward=0,
                catalog_id="anomaly.unknown", anomaly_kind=enemy.anomaly_kind,
                vision=enemy.vision, trait="phantom",
            )
            summon.glyph = enemy.glyph
            summon.main_id = enemy.id
            summon.active_skill_state["summon_expire"] = self.time + life
            summon.active_skill_state["summon_no_reward"] = True
            summon.alert_state = "追踪"
            self.messages.append(tr("{enemy}的执念落出一道残影！", enemy=tr(enemy.label)))
            return
        self.messages.append(tr("{enemy}想唤出残影，却找不到落脚处。", enemy=tr(enemy.label)))

    def _sk_allies_near(self, enemy: Entity, radius: int) -> list[Entity]:
        """声路内的同伴（失控意识、存活、有视线）。"""
        return [
            other for other in self.enemies
            if other is not enemy and other.integrity > 0 and other.relation == "失控意识"
            and max(abs(other.x - enemy.x), abs(other.y - enemy.y)) <= radius
            and self._has_line_of_sight(enemy.x, enemy.y, other.x, other.y)
        ]

    def _friendly_line_blocker(self, enemy: Entity, x0: int, y0: int,
                               x1: int, y1: int) -> Entity | None:
        """§8.3：射线上先于目标格出现的己方同伴（不隔着头开火）。"""
        cells = self._sk_ray(x0, y0, x1, y1, max(abs(x1 - x0), abs(y1 - y0)))
        for x, y in cells:
            if (x, y) == (x1, y1):
                break
            other = self.entity_at(x, y)
            if (other is not None and other is not enemy
                    and other.relation == "失控意识" and other.integrity > 0):
                return other
        return None

    def _ray_line_stale(self, enemy: Entity) -> bool:
        """§8.3：同一射击位上连续两次被躲开后，先换线再开火。

        只有确实存在另一条合法射击线时才放弃本次起手；无路可换时仍可按
        角色进攻（方案 §8.3 末条），不制造永久停火。
        """
        if not self._recent_whiff_any(enemy):
            return False
        from .pathing.pursuit import RANGED_DISTANCE_BANDS
        band = RANGED_DISTANCE_BANDS.get(getattr(enemy, "catalog_id", ""))
        if not band or not self._enemy_sees_player(enemy):
            return False
        return bool(self._ranged_position_step(
            enemy, (self.player.x, self.player.y), band))

    # ------------------------------------------------------------------
    # 技能 handler：caster 返回 (warning_cells, locked_path, target_cell, meta)
    # ------------------------------------------------------------------

    # ---- 弹道细线 ----

    def _cast_line(self, enemy: Entity, skill, binding):
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        cells = self._sk_player_line(enemy, skill)
        if not cells:
            return None
        if self._friendly_line_blocker(enemy, enemy.x, enemy.y,
                                       self.player.x, self.player.y):
            return None
        if self._ray_line_stale(enemy):
            return None
        return cells, None, None, {"overrides": dict(binding.overrides)}

    # ---- 位移 ----

    def _cast_model_push(self, enemy: Entity, skill, binding):
        # §15：相邻推挤也是「把玩家当目标」，同样要过目标资格。致盲／匿踪／
        # 遮挡下它不该还能精准地往玩家身上推。
        if not self._sk_player_visible(enemy, max(1, int(skill.max_range or 1))):
            return None
        if not self._adjacent_to_player(enemy):
            return None
        return [(self.player.x, self.player.y)], None, (self.player.x, self.player.y), {
            "push": True, "overrides": dict(binding.overrides),
        }

    def _cast_abyss_pull(self, enemy: Entity, skill, binding):
        if self._player_control_immune():
            return None
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        cells = self._sk_player_line(enemy, skill)
        if not cells:
            return None
        if self._friendly_line_blocker(enemy, enemy.x, enemy.y,
                                       self.player.x, self.player.y):
            return None
        return cells, None, None, {"pull": True, "overrides": dict(binding.overrides)}

    def _cast_echo_dash(self, enemy: Entity, skill, binding):
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        dist = max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y))
        if not (2 <= dist <= skill.max_range):
            return None
        if not self._has_line_of_sight(enemy.x, enemy.y, self.player.x, self.player.y):
            return None
        path = self._sk_ray(enemy.x, enemy.y, self.player.x, self.player.y, 2)
        if not path:
            return None
        return None, path, None, {"dash": True, "overrides": dict(binding.overrides)}

    _cast_return_charge = _cast_echo_dash

    def _resolve_dash(self, enemy: Entity, skill, pending: dict) -> None:
        """冲刺/抄写：沿锁定路径前进，撞到首个实体结束并造成一次创伤。"""
        if self._enemy_rooted(enemy):
            capture=getattr(self,'_cast_fx_capture',None)
            if capture is not None:capture.resolved_path=((enemy.x,enemy.y),)
            return
        path = [tuple(c) for c in pending.get("locked_path", [])]
        power = self._skill_power(enemy, skill)
        stop = None
        for index, (x, y) in enumerate(path):
            if self.cell(x, y).solid:
                stop = index
                break
            entity = self.entity_at(x, y)
            if entity is not None and entity is not enemy:
                stop = index
                break
        else:
            stop = len(path)
        # 落点：撞到处的前一格（或路径尽头）。
        landing = path[:stop]
        capture = getattr(self, '_cast_fx_capture', None)
        if capture is not None:
            capture.resolved_path = tuple(landing + (path[stop:stop+1]
                if stop < len(path) and not self.cell(*path[stop]).solid else []))
        if landing:
            lx, ly = landing[-1]
            if self.entity_at(lx, ly) is None and not self.cell(lx, ly).solid:
                enemy.x, enemy.y = lx, ly
        hit = stop < len(path) and (self.player.x, self.player.y) == path[stop]
        if hit:
            self._enemy_skill_trauma(enemy, power, skill.trauma_channel)
            self.messages.append(tr(
                "{enemy}沿预警线冲刺，正撞在你身上（{channel} {power}）！",
                enemy=tr(enemy.label), channel=tr(skill.trauma_channel), power=power,
            ))
        else:
            self.messages.append(tr("{enemy}沿预警线冲了过去，扑了个空。", enemy=tr(enemy.label)))

    def _cast_mirror_swap(self, enemy: Entity, skill, binding):
        # §13.4：镜像迁步原先只按实时距离选目标，隐身／致盲都拦不住。
        # 起手与普通感知同一口径（can_see／vanish／致盲），不再另造强感知通道。
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        dist = max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y))
        if not (2 <= dist <= skill.max_range):
            return None
        # 目的格：目标侧面可通行空格（至少存在一个才算合法）。
        free = [
            (nx, ny) for nx, ny in (
                (self.player.x + 1, self.player.y), (self.player.x - 1, self.player.y),
                (self.player.x, self.player.y + 1), (self.player.x, self.player.y - 1),
            )
            if self._sk_open(nx, ny) and self.entity_at(nx, ny) is None
        ]
        if not free:
            return None
        return None, None, None, {"swap": True, "overrides": dict(binding.overrides)}

    def _resolve_mirror_swap(self, enemy: Entity, skill, pending: dict) -> None:
        # §13.4：结算不能再拿玩家实时格补位——目标在蓄力中失去视觉（匿踪／致盲）
        # 时这一手落空；否则等于隐藏追踪。合法位置证据只认起手时仍看得见。
        if not self._sk_player_visible(enemy, skill.max_range):
            self.messages.append(tr("{enemy}的迁步在镜面里失了准头。", enemy=tr(enemy.label)))
            return
        for nx, ny in (
            (self.player.x + 1, self.player.y), (self.player.x - 1, self.player.y),
            (self.player.x, self.player.y + 1), (self.player.x, self.player.y - 1),
        ):
            if self._sk_open(nx, ny) and self.entity_at(nx, ny) is None:
                enemy.x, enemy.y = nx, ny
                self.messages.append(tr("{enemy}从镜子的另一侧走了出来！", enemy=tr(enemy.label)))
                return
        self.messages.append(tr("{enemy}的迁步被占死了。", enemy=tr(enemy.label)))

    # ---- 自身/同伴征兆 ----

    def _cast_fold_guard(self, enemy: Entity, skill, binding):
        st = self._skill_state(enemy)
        maximum = int(st.get("max_integrity") or enemy.integrity or 1)
        if enemy.integrity > maximum * 0.6 + 0.5:
            return None
        if any(pid in enemy.portents for pid in _GUARD_PORTENTS):
            return None
        return None, None, None, {"guard": "sk_guard_fold", "overrides": dict(binding.overrides)}

    def _resolve_fold_guard(self, enemy: Entity, skill, pending: dict) -> None:
        if self._apply_direct_portent(enemy, "sk_guard_fold", 2):
            self.messages.append(tr("{enemy}折起一面护折，挡在身前。", enemy=tr(enemy.label)))

    def _cast_choir_guard(self, enemy: Entity, skill, binding):
        targets = [enemy] + self._sk_allies_near(enemy, skill.max_range)[:2]
        targets = [t for t in targets if not any(pid in t.portents for pid in _GUARD_PORTENTS)]
        if not targets:
            return None
        return None, None, None, {"guard_targets": [t.id for t in targets], "overrides": dict(binding.overrides)}

    def _resolve_choir_guard(self, enemy: Entity, skill, pending: dict) -> None:
        ids = set((pending.get("meta") or {}).get("guard_targets", []))
        count = 0
        for target in self.enemies:
            if target.id not in ids or target.integrity <= 0:
                continue
            if any(pid in target.portents for pid in _GUARD_PORTENTS):
                continue  # 与护折取最大，不刷新已存在的护幕
            if self._apply_direct_portent(target, "sk_guard_choir", 2):
                count += 1
        if count:
            self.messages.append(tr("和声织成护幕，罩住了 {n} 个身影。", n=count))

    def _cast_wake_allies(self, enemy: Entity, skill, binding):
        allies = [
            a for a in self._sk_allies_near(enemy, skill.max_range)
            if a.alert_state == "追踪" and "sk_guidance" not in a.portents
        ][:2]
        if not allies:
            return None
        return None, None, None, {"guidance": [a.id for a in allies], "overrides": dict(binding.overrides)}

    def _resolve_wake_allies(self, enemy: Entity, skill, pending: dict) -> None:
        ids = set((pending.get("meta") or {}).get("guidance", []))
        count = 0
        for target in self.enemies:
            if (target.id in ids and target.integrity > 0
                    and self._apply_direct_portent(target, "sk_guidance", 2)):
                count += 1
        if count:
            self.messages.append(tr("牧梦者的指引落在 {n} 个同伴脚下。", n=count))

    def _cast_echo_alert(self, enemy: Entity, skill, binding):
        if enemy.alert_state == "未察觉":
            return None
        allies = self._sk_allies_near(enemy, skill.max_range)[:2]
        if not allies:
            return None
        return None, None, None, {"alert": [a.id for a in allies], "overrides": dict(binding.overrides)}

    def _echo_report_point(self, enemy: Entity) -> "tuple[int, int]":
        """报信点＝报信者**自己知道**的那个位置，不是玩家实时格。

        2026-10-22（残余清单 A5）：`echo_alert` 与 `core_cry` 过去把
        `self.player.x/y` 直接写进友军的 ``last_seen_*``——等于让一个没看见
        玩家的施法者替全队**实时定位**，与 `_propagate_alert` 的口径（传信只记
        报信点，不冒充目击）矛盾，也让隐身／致盲形同无效。
        现在统一取施法者最后一次看见玩家的位置；从未看见过就退回施法者自己
        的格子（同伴去那边查看，而不是直接扑向玩家脚下）。
        """
        if enemy is not None and enemy.last_seen_x >= 0 and enemy.last_seen_y >= 0:
            return int(enemy.last_seen_x), int(enemy.last_seen_y)
        return int(enemy.x), int(enemy.y)

    def _resolve_echo_alert(self, enemy: Entity, skill, pending: dict) -> None:
        ids = set((pending.get("meta") or {}).get("alert", []))
        if not ids:
            return
        point = self._echo_report_point(enemy)
        count = 0
        for target in self.enemies:
            if target.id in ids and target.integrity > 0:
                target.last_seen_x, target.last_seen_y = point
                target.last_reported_x, target.last_reported_y = point
                target.last_reported_time = self.time
                target.alert_state = "追踪"
                self._remember_investigation(target, point[0], point[1],
                                             "report", "report")
                count += 1
        if count:
            self.messages.append(tr("点名回声把报信者知道的旧位置交给了 {n} 个同伴。", n=count))

    def _cast_shadow_step(self, enemy: Entity, skill, binding):
        if enemy.alert_state == "未察觉":
            return None
        # §15：这里原来直接读玩家实时坐标量距离。看不见的时候它只该用自己
        # 仍然有效的目击记忆；连记忆都没有，就说明它连「玩家离多远」都不知道，
        # 那就不该为了「离得够远」而起手。
        if self._sk_perceives_player(enemy):
            px, py = self.player.x, self.player.y
        else:
            memory = self._visual_memory_target(enemy)
            if memory is None:
                return None
            px, py = int(memory[0]), int(memory[1])
        dist = max(abs(enemy.x - px), abs(enemy.y - py))
        if dist < 3 or "sk_light_step" in enemy.portents:
            return None
        return None, None, None, {"light_step": True, "overrides": dict(binding.overrides)}

    def _resolve_shadow_step(self, enemy: Entity, skill, pending: dict) -> None:
        if self._apply_direct_portent(enemy, "sk_light_step", 2):
            self.messages.append(tr("{enemy}的脚步卸掉了重量。", enemy=tr(enemy.label)))

    def _cast_edit_heal(self, enemy: Entity, skill, binding):
        st = self._skill_state(enemy)
        # 预算由 _ensure_skill_budgets 在遭遇生命周期入口建立；候选查询只读。
        if int(st.get("heal_budget", 0)) <= 0:
            return None
        candidates = [enemy] + [
            a for a in self._sk_allies_near(enemy, skill.max_range)
            if a.integrity > 0 and a.anomaly_kind == enemy.anomaly_kind
        ]
        target = next((t for t in candidates if 0 < t.integrity * 2 <= self._sk_enemy_max(t)), None)
        if target is None:
            return None
        return None, None, None, {"heal_target": target.id, "overrides": dict(binding.overrides)}

    @staticmethod
    def _sk_enemy_max(enemy: Entity) -> int:
        from .content import ANOMALY_DEFINITIONS

        return max(1, int(ANOMALY_DEFINITIONS.get(enemy.catalog_id, {}).get("integrity", enemy.integrity)))

    def _resolve_edit_heal(self, enemy: Entity, skill, pending: dict) -> None:
        st = self._skill_state(enemy)
        target_id = (pending.get("meta") or {}).get("heal_target")
        target = next((e for e in self.enemies if e.id == target_id and e.integrity > 0), enemy)
        amount = min(2, int(st.get("heal_budget", 0)), max(0, self._sk_enemy_max(target) // 2 - target.integrity))
        if amount <= 0:
            return
        st["heal_budget"] = int(st.get("heal_budget", 0)) - amount
        target.integrity += amount
        self.messages.append(tr("{enemy}修订了自己——完整度 +{n}（预算剩 {left}）。",
                                enemy=tr(target.label), n=amount, left=st["heal_budget"]))

    def _cast_scribe_revision(self, enemy: Entity, skill, binding):
        st = self._skill_state(enemy)
        phase = self._enemy_skill_phase(enemy)
        used = st.get("revision_phases", [])
        if phase in used:
            return None
        negative = [
            pid for pid, turns in enemy.portents.items()
            if turns > 0 and self._sk_portent_kind(pid) == "负面"
        ]
        player_negative = [
            pid for pid, turns in self.portents.items()
            if turns > 0 and self._sk_portent_kind(pid) == "负面"
        ]
        if not negative and not player_negative:
            return None
        return None, None, None, {"revision_phase": phase, "overrides": dict(binding.overrides)}

    @staticmethod
    def _sk_portent_kind(portent_id: str) -> str:
        from ..materials import portent_def

        definition = portent_def(portent_id)
        return definition.kind if definition else ""

    def _resolve_scribe_revision(self, enemy: Entity, skill, pending: dict) -> None:
        from ..materials import portent_def as _portent_def

        st = self._skill_state(enemy)
        phase = (pending.get("meta") or {}).get("revision_phase", 1)
        st.setdefault("revision_phases", [])
        if phase in st["revision_phases"]:
            return
        st["revision_phases"].append(phase)
        cleansed = 0
        for holder in (enemy, self.player):
            for pid in list(holder.portents):
                definition = _portent_def(pid)
                if definition is None or definition.kind != "负面":
                    continue
                self._remember_portent_end(holder, pid)
                cleansed += 1
                break
        self.restore_resource('imagination', 1)
        self.messages.append(tr("共同校订抹平了批注：各自的负面征兆被划去一笔，想象力 +1。"))
        if cleansed == 0:
            self.messages.append(tr("墨迹无处可划——校订落空了。"))

    # ---- 负面征兆（玩家） ----

    def _cast_player_cell_portent(self, enemy: Entity, skill, binding):
        """落点为玩家所在单格的负面征兆（可见才成立；预警单格）。"""
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        return [(self.player.x, self.player.y)], None, (self.player.x, self.player.y), {
            "overrides": dict(binding.overrides),
        }

    def _sk_perceives_player(self, enemy: Entity) -> bool:
        """这个实体此刻是否**合法地**感知到玩家（不带射程约束）。

        匿踪与视觉判定都在这里收口：`vanish_turns` 不算看见（它已经不在视野里），
        遮蔽／致盲由 `can_see` 决定。凡是「要不要按玩家当前位置做判断」的地方
        都该先问这一句，而不是直接读 `player.x/y`。
        """
        if getattr(self, "vanish_turns", 0) > 0:
            return False
        return self.can_see(enemy, self.player.x, self.player.y)

    def _sk_player_visible(self, enemy: Entity, max_range: int) -> bool:
        """技能目标资格与普通感知同一口径（docs 261022 AI §4／§12 P0）。

        距离、视野、遮挡、致盲与匿踪统一由 ``can_see`` 决定；``max_range``
        只额外收紧技能射程，不能在施法通道另造一套更强的感知。
        """
        if max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y)) > max_range:
            return False
        return self._sk_perceives_player(enemy)

    def _skill_position_evidence(self, enemy: Entity, skill) -> tuple[int, int] | None:
        """§8.1 声源盲投：看不见玩家时，取仍然有效的「位置证据」的格子。

        证据只来自本体已经合法得到的事实，不读玩家实时坐标：
        1. 仍然有效的最后目击点（`_visual_memory_target` 已带期限）；
        2. 未尝试、未挂起、未过期的调查任务点（声音／传信／目击任务）；
        3. 同伴报信点（`last_reported_*`）。
        取射程内的第一个；没有任何证据返回 None——没有证据就不起手。
        """
        candidates: list[tuple[int, int]] = []
        memory = self._visual_memory_target(enemy)
        if memory is not None:
            candidates.append((int(memory[0]), int(memory[1])))
        now = int(self.time)
        for task in getattr(enemy, "investigation_tasks", ()) or ():
            if task.get("tried") or task.get("unreachable"):
                continue
            if int(task.get("expires", 0)) <= now:
                continue
            candidates.append((int(task.get("x", -1)), int(task.get("y", -1))))
        reported_x = int(getattr(enemy, "last_reported_x", -1))
        reported_y = int(getattr(enemy, "last_reported_y", -1))
        if reported_x >= 0 and reported_y >= 0:
            candidates.append((reported_x, reported_y))
        for x, y in candidates:
            if not (0 <= x < self.width and 0 <= y < self.height):
                continue
            if max(abs(enemy.x - x), abs(enemy.y - y)) > skill.max_range:
                continue
            return x, y
        return None

    def _resolve_clock_drag(self, enemy: Entity, skill, pending: dict) -> None:
        if (self.player.x, self.player.y) != tuple(pending.get("target_cell") or ()):
            self._note_skill_miss(enemy, skill)
            self.messages.append(tr("你离开了落点——迟拍落空了。"))
            return
        if self.portents.get("sk_late_beat", 0) > 0:
            return
        self._grant_portent_direct(self.player, "sk_late_beat")
        self.messages.append(tr("节拍慢了一拍：移动额外耗时 +0.3（迟拍 2 回合）。"))

    def _resolve_seam_bind(self, enemy: Entity, skill, pending: dict) -> None:
        if (self.player.x, self.player.y) != tuple(pending.get("target_cell") or ()):
            self._note_skill_miss(enemy, skill)
            self.messages.append(tr("你离开了落点——缝影钉了个空。"))
            return
        if self.portents.get("sk_seam_shadow", 0) <= 0:
            self._grant_portent_direct(self.player, "sk_seam_shadow")
            self.messages.append(tr("影子被缝在原地：下一次移动 +0.5（缝影）。"))
        power = self._skill_power(enemy, skill)
        if power > 0:
            self._enemy_skill_trauma(enemy, power, skill.trauma_channel)

    def _resolve_mislabel(self, enemy: Entity, skill, pending: dict) -> None:
        if (self.player.x, self.player.y) != tuple(pending.get("target_cell") or ()):
            self._note_skill_miss(enemy, skill)
            self.messages.append(tr("你离开了落点——标签贴空了。"))
            return
        if self.portents.get("sk_blur", 0) > 0:
            return
        self._grant_portent_direct(self.player, "sk_blur")
        self.messages.append(tr("标签贴错了位置：视野 −1（失焦；只有本项最多减到 3）。"))

    def _resolve_lullaby(self, enemy: Entity, skill, pending: dict) -> None:
        warned = {tuple(c) for c in pending.get("warning_cells", [])}
        if (self.player.x, self.player.y) not in warned:
            self._note_skill_miss(enemy, skill)
            self.messages.append(tr("你退出了摇篮曲的落点。"))
            return
        if self.portents.get("sk_drowsy", 0) > 0:
            return
        self._grant_portent_direct(self.player, "sk_drowsy")
        self.messages.append(tr("摇篮曲在脚踝上打了个结：下一次移动 +0.5（倦意）。"))

    def _cast_lullaby(self, enemy: Entity, skill, binding):
        if self._player_control_immune():
            return None
        if self.portents.get("sk_drowsy", 0) > 0:
            return None
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        cells = self._sk_cross(self.player.x, self.player.y, 2)
        return cells, None, None, {"overrides": dict(binding.overrides)}

    def _cast_oblivion_mark(self, enemy: Entity, skill, binding):
        if self._player_control_immune():
            return None
        if self.portents.get("sk_faded_ink", 0) > 0 or self.imagination <= 0:
            return None
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        return [(self.player.x, self.player.y)], None, (self.player.x, self.player.y), {
            "overrides": dict(binding.overrides),
        }

    def _resolve_oblivion_mark(self, enemy: Entity, skill, pending: dict) -> None:
        if (self.player.x, self.player.y) != tuple(pending.get("target_cell") or ()):
            self._note_skill_miss(enemy, skill)
            self.messages.append(tr("你离开了落点——遗忘批注没有落上。"))
            return
        self._grant_portent_direct(self.player, "sk_faded_ink")
        overrides = (pending.get("meta") or {}).get("overrides") or {}
        drain = int(overrides.get("imagination_drain", 0))
        if drain:
            from .settlement import REASON_COMBAT, settle_delta
            settle_delta(self, 'imagination', -min(drain, self.imagination),
                         reason=REASON_COMBAT, source='异象技能抽取')

        power = self._skill_power(enemy, skill)
        if power > 0:
            self._enemy_skill_trauma(enemy, power, skill.trauma_channel)
        self.messages.append(tr("淡墨批注落在你身上：想象力将逐回合消褪（共 2 点）。"))

    def _cast_redact_buff(self, enemy: Entity, skill, binding):
        # §13.4：涂黑正面征兆的落点原为玩家实时格，无任何视觉判定。
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        candidates = [
            pid for pid, turns in self.portents.items()
            if turns > 0 and self._sk_portent_kind(pid) == "正面"
        ]
        if not candidates:
            return None
        return [(self.player.x, self.player.y)], None, None, {"overrides": dict(binding.overrides)}

    def _resolve_redact_buff(self, enemy: Entity, skill, pending: dict) -> None:
        candidates = [
            pid for pid, turns in self.portents.items()
            if turns > 0 and self._sk_portent_kind(pid) == "正面"
        ]
        if not candidates:
            return
        # 固定优先：护罩类 → 轻步类 → 其余正面征兆。
        def priority(pid: str) -> int:
            if "guard" in pid or "shield" in pid or "mirror" in pid:
                return 0
            if "light_step" in pid:
                return 1
            return 2

        candidates.sort(key=priority)
        victim = candidates[0]
        self._remember_portent_end(self.player, victim)
        from ..materials import portent_def as _pd

        name = _pd(victim).name if _pd(victim) else victim
        self.messages.append(tr("它一划，把你身上的「{name}」涂黑了。", name=tr(name)))

    def _cast_core_pause(self, enemy: Entity, skill, binding):
        if self._player_control_immune():
            return None
        if self.portents.get("sk_rooted", 0) > 0:
            return None
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        return [(self.player.x, self.player.y)], None, (self.player.x, self.player.y), {
            "overrides": dict(binding.overrides),
        }

    def _resolve_core_pause(self, enemy: Entity, skill, pending: dict) -> None:
        if self.difficulty_revision >= 3 and not self.realm_id and self._player_control_immune():
            return
        if (self.player.x, self.player.y) != tuple(pending.get("target_cell") or ()):
            self._note_skill_miss(enemy, skill)
            self.messages.append(tr("句号没能把你顿住——你提前离开了那格。"))
            return
        self._grant_portent_direct(self.player, "sk_rooted")
        self._skill_grant_control_immunity()
        self.messages.append(tr("句子被迫停顿：接下来 1 回合你不能移动（道具、构想、攻击仍可用）。"))

    # ---- 场 ----

    def _cast_slow_pool(self, enemy: Entity, skill, binding):
        if any(f.get("source_id") == enemy.id and f.get("family") == "slow_frame" for f in self.enemy_skill_fields):
            return None
        if self._sk_player_visible(enemy, skill.max_range):
            cx, cy = self._suppression_anchor(enemy, skill, (self.player.x, self.player.y))
            meta = {"overrides": dict(binding.overrides)}
        else:
            evidence = self._skill_position_evidence(enemy, skill)
            if evidence is None:
                return None
            cx, cy = evidence
            meta = {"blind_cast": True, "evidence": [cx, cy],
                    "overrides": dict(binding.overrides)}
        cells = self._sk_cross(cx, cy, 2)
        meta["field"] = ("slow_frame", "无", cells, 4, 0, 0, False)
        return cells, None, None, meta

    def _cast_ink_pool(self, enemy: Entity, skill, binding):
        if any(f.get("source_id") == enemy.id and f.get("family") == "ink" for f in self.enemy_skill_fields):
            return None
        if self._sk_player_visible(enemy, skill.max_range):
            cx, cy = self._suppression_anchor(enemy, skill, (self.player.x, self.player.y))
            meta = {"overrides": dict(binding.overrides)}
        else:
            evidence = self._skill_position_evidence(enemy, skill)
            if evidence is None:
                return None
            cx, cy = evidence
            meta = {"blind_cast": True, "evidence": [cx, cy],
                    "overrides": dict(binding.overrides)}
        cells = self._sk_cross(cx, cy, 2)
        meta["field"] = ("ink", "无", cells, 4, 0, 0, False)
        return cells, None, None, meta

    def _cast_fog_veil(self, enemy: Entity, skill, binding):
        if any(f.get("source_id") == enemy.id and f.get("family") == "fog" for f in self.enemy_skill_fields):
            return None
        # 落在敌我之间：薄雾以连线中点为心。看不见玩家时投到位置证据（声源盲投）。
        if self._sk_player_visible(enemy, skill.max_range):
            mx = (enemy.x + self.player.x) // 2
            my = (enemy.y + self.player.y) // 2
            meta = {"overrides": dict(binding.overrides)}
        else:
            evidence = self._skill_position_evidence(enemy, skill)
            if evidence is None:
                return None
            mx = (enemy.x + evidence[0]) // 2
            my = (enemy.y + evidence[1]) // 2
            meta = {"blind_cast": True, "evidence": list(evidence),
                    "overrides": dict(binding.overrides)}
        cells = self._sk_cross(mx, my, 2)
        meta["field"] = ("fog", "无", cells, 4, 0, 0, False)
        return cells, None, None, meta

    def _cast_nightmare_patch(self, enemy: Entity, skill, binding):
        if any(f.get("source_id") == enemy.id and f.get("family") == "dream_thorn" for f in self.enemy_skill_fields):
            return None
        if self._sk_player_visible(enemy, skill.max_range):
            cx, cy = self._suppression_anchor(enemy, skill, (self.player.x, self.player.y))
            meta = {"overrides": dict(binding.overrides)}
        else:
            evidence = self._skill_position_evidence(enemy, skill)
            if evidence is None:
                return None
            cx, cy = evidence
            meta = {"blind_cast": True, "evidence": [cx, cy],
                    "overrides": dict(binding.overrides)}
        cells = self._sk_diamond(cx, cy, 2)
        meta["field"] = ("dream_thorn", "心智", cells, 4,
                         int(TUNING["field_tick_damage"]), 2, True)
        return cells, None, None, meta

    def _cast_core_chill(self, enemy: Entity, skill, binding):
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        if any(f.get("source_id") == enemy.id and f.get("family") == "frost" for f in self.enemy_skill_fields):
            return None
        cx, cy = self._suppression_anchor(enemy, skill, (self.player.x, self.player.y))
        cells = self._sk_hline(cx, cy, enemy.x, 5)
        return cells, None, None, {"field": ("frost", "无", cells, 4, 0, 0, False), "overrides": dict(binding.overrides)}

    def _cast_fire_seed(self, enemy: Entity, skill, binding):
        if enemy.alert_state == "未察觉":
            return None
        if any(f.get("source_id") == enemy.id and f.get("family") == "ember" for f in self.enemy_skill_fields):
            return None
        ax, ay = enemy.last_seen_x, enemy.last_seen_y
        if ax < 0:
            ax, ay = self.player.x, self.player.y
        if not (0 <= ax < self.width and 0 <= ay < self.height):
            return None
        cells = self._sk_hline(ax, ay, enemy.x, 5)
        cells = [
            (x, y) for x, y in cells
            if not self.cell(x, y).solid and self.cell(x, y).liquid == 0
            and not self._sk_fireproof_floor(x, y)
        ]
        if not cells:
            return None
        return cells, None, None, {"field": ("ember", "清醒", cells, 4, 0, 0, False), "overrides": dict(binding.overrides)}

    def _sk_fireproof_floor(self, x: int, y: int) -> bool:
        from ..materials import floor_effect_for

        return bool(floor_effect_for(self.cell(x, y)).fireproof)

    def _resolve_fire_seed(self, enemy: Entity, skill, pending: dict) -> None:
        cells = [tuple(c) for c in pending.get("warning_cells", [])]
        lit = 0
        for x, y in cells:
            if self._ignite_cell(x, y, strength=3):
                lit += 1
        if lit:
            self._sk_add_field(enemy, "ember", cells, channel="清醒", rounds=4,
                               note=tr("三点焚歌的余烬熄了。"))
            self.messages.append(tr("{enemy}唱出三点焚歌——火线烧起来了！", enemy=tr(enemy.label)))
        else:
            self.messages.append(tr("焚歌落在湿冷处，没有燃起来。"))

    def _cast_electric_stitch(self, enemy: Entity, skill, binding):
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        # 导电落点：以玩家为心的四邻里，含液体/金属导体的格。
        cells = [
            (x, y) for x, y in self._sk_cross(self.player.x, self.player.y, 2)
            if self.cell(x, y).liquid >= 8 or self.cell(x, y).wall_kind == "金属墙"
        ]
        if not cells:
            return None
        return cells[: skill.max_cells], None, None, {"overrides": dict(binding.overrides)}

    def _resolve_electric_stitch(self, enemy: Entity, skill, pending: dict) -> None:
        cells = [tuple(c) for c in pending.get("warning_cells", [])]
        power = self._skill_power(enemy, skill)
        if (self.player.x, self.player.y) in cells:
            self._enemy_skill_trauma(enemy, power, skill.trauma_channel)
            self.messages.append(tr("导忆电针扎进导体，把你电了个正着（清醒 {power}）！", power=power))
        else:
            self.messages.append(tr("电针落在导体上，余电沿着液面爬开。"))
        # 余电：每回合 1 共 2 次；电痉挛移步 +0.3（1 回合）。
        self._sk_add_field(enemy, "spark", cells, channel="清醒", rounds=4,
                           tick_damage=int(TUNING["field_tick_damage"]), max_ticks=2,
                           note=tr("余电耗尽了。"))
        for holder in [self.player] + [e for e in self.enemies if e.integrity > 0]:
            if (holder.x, holder.y) in cells:
                self._apply_direct_portent(holder, "shocked", 1)

    def _cast_gift_bomb(self, enemy: Entity, skill, binding):
        dist = max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y))
        if not (2 <= dist <= skill.max_range):
            return None
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        if not self._has_line_of_sight(enemy.x, enemy.y, self.player.x, self.player.y):
            return None
        if any(f.get("source_id") == enemy.id and f.get("family") == "fuse" for f in self.enemy_skill_fields):
            return None  # 每来源最多 1 枚
        cells = self._sk_cross(self.player.x, self.player.y, 2)
        return cells, None, None, {"push": True, "overrides": dict(binding.overrides)}

    def _resolve_gift_bomb(self, enemy: Entity, skill, pending: dict) -> None:
        warned = {tuple(c) for c in pending.get("warning_cells", [])}
        if (self.player.x, self.player.y) not in warned:
            self.messages.append(tr("礼盒拆了个空——你不在爆点上。"))
            return
        power = self._skill_power(enemy, skill)
        self._enemy_skill_trauma(enemy, power, skill.trauma_channel)
        self._skill_push_player(enemy, away=True)
        self.messages.append(tr("礼盒炸开——纸屑里全是冲击（清醒 {power}）！", power=power))

    def _cast_space_fold(self, enemy: Entity, skill, binding):
        if enemy.alert_state == "未察觉":
            return None
        if any(f.get("source_id") == enemy.id and f.get("family") == "fold" for f in self.enemy_skill_fields):
            return None
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        if not self._has_line_of_sight(enemy.x, enemy.y, self.player.x, self.player.y):
            return None
        dist = max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y))
        if dist < 2 or dist > skill.max_range:
            return None
        # 临时折面：连线中段最多 2 格可通行的非保护地形。
        line = self._sk_ray(enemy.x, enemy.y, self.player.x, self.player.y, dist)
        cells = [
            (x, y) for x, y in line[:2]
            if not self.cell(x, y).solid and self.cell(x, y).wall_kind not in self._SKILL_PROTECTED_WALLS
        ]
        if not cells:
            return None
        return cells, None, None, {"field": ("fold", "无", cells, int(skill.duration_rounds), 0, 0, False), "overrides": dict(binding.overrides)}

    def _cast_vine_grow(self, enemy: Entity, skill, binding):
        if any(f.get("source_id") == enemy.id and f.get("family") == "root" for f in self.enemy_skill_fields):
            return None  # 该来源无存活根丝才施放
        cells = [
            (enemy.x + dx, enemy.y + dy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1))
            if self._sk_open(enemy.x + dx, enemy.y + dy)
        ][: skill.max_cells]
        if not cells:
            return None
        return cells, None, None, {
            "field": ("root", "无", cells, int(skill.duration_rounds), 0, 0, False),
            "overrides": dict(binding.overrides),
        }

    def _resolve_field_only(self, enemy: Entity, skill, pending: dict) -> None:
        """场的结算就是登记效果场（预警格即实际格）。"""
        spec = (pending.get("meta") or {}).get("field")
        if not spec:
            return
        family, channel, cells, rounds, tick_damage, max_ticks, damage_enemies = spec
        covered = {tuple(c) for c in cells}
        self._sk_add_field(enemy, family, [tuple(c) for c in cells], channel=channel,
                           rounds=rounds, tick_damage=tick_damage, max_ticks=max_ticks,
                           damage_enemies=damage_enemies)
        if (skill.skill_id in SUPPRESSION_FIELD_SKILLS
                and (self.player.x, self.player.y) not in covered):
            # §8.3：玩家从头到尾没进场，这次施法没有实际收益，记一次落空。
            self._note_skill_miss(enemy, skill)
        names = {
            "slow_frame": tr("{enemy}投下迟帧光斑——光里的脚步会变慢。", enemy=tr(enemy.label)),
            "ink": tr("{enemy}倾下一滩墨——墨迹里行走会拖沓。", enemy=tr(enemy.label)),
            "fog": tr("{enemy}吐出一口薄雾——雾里看不清远处。", enemy=tr(enemy.label)),
            "dream_thorn": tr("{enemy}缝上一块噩梦补丁——刺会在梦里长出来。", enemy=tr(enemy.label)),
            "frost": tr("{enemy}的冻嚎在地上留下成排寒痕。", enemy=tr(enemy.label)),
            "fold": tr("{enemy}把房间折起一道临时折面——弹道会被挡住。", enemy=tr(enemy.label)),
            "root": tr("{enemy}的根丝从盆里蔓延出来。", enemy=tr(enemy.label)),
        }
        self.messages.append(names.get(family, tr("「{skill}」落定了。", skill=tr(skill.name_zh))))

    def _cast_cool_drain(self, enemy: Entity, skill, binding):
        cells = self._sk_cross(enemy.x, enemy.y, 3)
        cells = [
            (x, y) for x, y in cells
            if (self.cell(x, y).liquid > 0 or self.cell(x, y).gas > 0)
            and self.cell(x, y).liquid_kind != "以太"
        ]
        if not cells:
            return None
        return cells, None, None, {"overrides": dict(binding.overrides)}

    def _resolve_cool_drain(self, enemy: Entity, skill, pending: dict) -> None:
        drained = 0
        for x, y in [tuple(c) for c in pending.get("warning_cells", [])]:
            cell = self.cell(x, y)
            if cell.liquid > 0:
                cell.liquid = max(0, cell.liquid - 8)
                if cell.liquid == 0:
                    cell.liquid_kind = ""
                drained += 1
            if cell.gas > 0:
                cell.gas = max(0, cell.gas - 8)
                if cell.gas == 0:
                    cell.gas_kind = ""
                drained += 1
        if drained:
            self._material_index_ready = False
            self.messages.append(tr("{enemy}凝出一圈寒霜，抽干了周围的介质。", enemy=tr(enemy.label)))

    def _cast_stair_fracture(self, enemy: Entity, skill, binding):
        cells = [
            (x, y)
            for y in range(max(0, enemy.y - 3), min(self.height, enemy.y + 4))
            for x in range(max(0, enemy.x - 3), min(self.width, enemy.x + 4))
            if self.cell(x, y).solid and self.cell(x, y).wall_kind
            and not self._protected_wall(self.cell(x, y).wall_kind)
        ][: skill.max_cells]
        if not cells:
            return None
        return cells, None, None, {"overrides": dict(binding.overrides)}

    def _resolve_stair_fracture(self, enemy: Entity, skill, pending: dict) -> None:
        broken = 0
        for x, y in [tuple(c) for c in pending.get("warning_cells", [])]:
            cell = self.cell(x, y)
            if not cell.solid or not cell.wall_kind or self._protected_wall(cell.wall_kind):
                continue
            cell.integrity -= 20
            broken += 1
            if cell.integrity <= 0:
                cell.solid = False
                cell.wall_kind = ""
                cell.hardness = 0
        if broken:
            self._material_index_ready = False
            self.messages.append(tr("{enemy}身侧的阶沿崩解剥落。", enemy=tr(enemy.label)))

    def _cast_scribe_erase(self, enemy: Entity, skill, binding):
        # §13.4：抹擦十字原以玩家实时格为中心，无任何视觉判定。
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        cells = self._sk_cross(self.player.x, self.player.y, 2)
        has_field = any(
            (c[0], c[1]) in self._sk_field_cells() for c in cells
        )
        walls = [
            (x, y) for x, y in cells
            if self.cell(x, y).solid and self.cell(x, y).wall_kind
            and not self._protected_wall(self.cell(x, y).wall_kind)
        ][:1]
        if not has_field and not walls:
            return None
        return cells, None, None, {"overrides": dict(binding.overrides)}

    def _resolve_scribe_erase(self, enemy: Entity, skill, pending: dict) -> None:
        warned = {tuple(c) for c in pending.get("warning_cells", [])}
        erased = 0
        for field in self.enemy_skill_fields:
            kept = [c for c in field.get("cells", []) if (c[0], c[1]) not in warned]
            erased += len(field.get("cells", [])) - len(kept)
            field["cells"] = kept
        self.enemy_skill_fields = [f for f in self.enemy_skill_fields if f.get("cells")]
        walls = 0
        for x, y in list(warned):
            cell = self.cell(x, y)
            if cell.solid and cell.wall_kind and not self._protected_wall(cell.wall_kind):
                cell.integrity -= 20
                walls += 1
                if cell.integrity <= 0:
                    cell.solid = False
                    cell.wall_kind = ""
                    cell.hardness = 0
        if erased or walls:
            self._material_index_ready = False
            self.messages.append(tr("执笔者抬笔一擦——局部的存在被抹去了。"))

    # ---- 范围/核心 ----

    def _cast_core_period(self, enemy: Entity, skill, binding):
        if self._player_control_immune():
            return None
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        cells = self._sk_diamond(self.player.x, self.player.y, 2)
        return cells, None, None, {
            "imagination_hit": 1, "overrides": dict(binding.overrides),
        }

    def _cast_core_beacon(self, enemy: Entity, skill, binding):
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        cells = self._sk_cone90(enemy.x, enemy.y, self.player.x, self.player.y, 4, skill.max_cells)
        if not cells:
            return None
        return cells, None, None, {"overrides": dict(binding.overrides)}

    def _cast_core_cry(self, enemy: Entity, skill, binding):
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        cells = self._sk_diamond(self.player.x, self.player.y, 3)
        overrides = dict(binding.overrides)
        if overrides.get("shape"):
            cells = self._sk_diamond(self.player.x, self.player.y, 2)
        return cells, None, None, {"overrides": overrides}

    def _resolve_core_cry(self, enemy: Entity, skill, pending: dict) -> None:
        warned = {tuple(c) for c in pending.get("warning_cells", [])}
        hit = (self.player.x, self.player.y) in warned
        if hit:
            power = self._skill_power(enemy, skill)
            self._enemy_skill_trauma(enemy, power, skill.trauma_channel)
            self.messages.append(tr("初啼声浪碾过你的意识（心智 {power}）！", power=power))
        else:
            self.messages.append(tr("声浪滚过菱形范围，你已在浪外。"))
        overrides = (pending.get("meta") or {}).get("overrides") or {}
        if not overrides.get("alert_allies", True):
            return
        allies = self._sk_allies_near(enemy, skill.max_range)[:2]
        if not allies:
            return
        # 同上：初啼只是把施法者知道的位置喊给同伴，不是实时定位。
        point = self._echo_report_point(enemy)
        for target in allies:
            target.last_seen_x, target.last_seen_y = point
            target.last_reported_x, target.last_reported_y = point
            target.last_reported_time = self.time
            target.alert_state = "追踪"
            self._remember_investigation(target, point[0], point[1], "report", "report")

    def _cast_scribe_draft(self, enemy: Entity, skill, binding):
        if not self._sk_player_visible(enemy, skill.max_range):
            return None
        cells = self._sk_diamond(self.player.x, self.player.y, 3)
        return cells, None, None, {"blur_on_hit": True, "overrides": dict(binding.overrides)}

    # ---- 召唤 ----

    def _cast_split_echo(self, enemy: Entity, skill, binding):
        overrides = dict(binding.overrides)
        same_max = int(overrides.get("same_source_summon_max", 1))
        if self._sk_summon_alive(enemy.id) >= same_max:
            return None
        if self._sk_total_summons() >= int(TUNING["summon_limit"]):
            return None
        if not self._sk_open(enemy.x + 1, enemy.y) and not any(
            self._sk_open(enemy.x + dx, enemy.y + dy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ):
            return None
        return None, None, None, {"summon": ("split_echo", overrides)}

    def _cast_core_summon(self, enemy: Entity, skill, binding):
        if self._sk_summon_alive(enemy.id) >= 2:  # 同源上限 2
            return None
        if self._sk_total_summons() >= int(TUNING["summon_limit"]):
            return None
        if not self._sk_summon_spots(enemy):
            return None
        return None, None, None, {"summon": ("core_summon", dict(binding.overrides))}

    def _sk_total_summons(self) -> int:
        return sum(
            1 for e in self.enemies
            if e.integrity > 0 and e.trait == "phantom"
            and (e.active_skill_state or {}).get("summon_expire") is not None
        )

    def _resolve_summon(self, enemy: Entity, skill, pending: dict) -> None:
        spec = (pending.get("meta") or {}).get("summon")
        if not spec:
            return
        kind, overrides = spec
        variant = str(overrides.get("summon_variant", ""))
        if kind == "split_echo":
            self._sk_spawn_summon(enemy, integrity=2, life=4, attack_time=2.0, variant=variant)
        else:
            self._sk_spawn_summon(enemy, integrity=3, life=5, attack_time=2.0, variant=variant)

    # ------------------------------------------------------------------
    # 注册表
    # ------------------------------------------------------------------

    _SKILL_CASTERS = {}  # 类体填充（见文件末尾）
    _SKILL_RESOLVERS = {}


_SKILL_CASTERS: dict[str, Any] = {
    # 弹道细线
    "paper_dart": EnemySkillMixin._cast_line,
    "light_trace": EnemySkillMixin._cast_line,
    "mind_bite": EnemySkillMixin._cast_line,
    "null_ray": EnemySkillMixin._cast_line,
    "scribe_stroke": EnemySkillMixin._cast_line,
    # 位移
    "model_push": EnemySkillMixin._cast_model_push,
    "abyss_pull": EnemySkillMixin._cast_abyss_pull,
    "echo_dash": EnemySkillMixin._cast_echo_dash,
    "return_charge": EnemySkillMixin._cast_return_charge,
    "mirror_swap": EnemySkillMixin._cast_mirror_swap,
    # 自身/同伴征兆
    "fold_guard": EnemySkillMixin._cast_fold_guard,
    "choir_guard": EnemySkillMixin._cast_choir_guard,
    "wake_allies": EnemySkillMixin._cast_wake_allies,
    "echo_alert": EnemySkillMixin._cast_echo_alert,
    "shadow_step": EnemySkillMixin._cast_shadow_step,
    "edit_heal": EnemySkillMixin._cast_edit_heal,
    "scribe_revision": EnemySkillMixin._cast_scribe_revision,
    # 负面征兆（玩家）
    "clock_drag": EnemySkillMixin._cast_player_cell_portent,
    "seam_bind": EnemySkillMixin._cast_player_cell_portent,
    "mislabel": EnemySkillMixin._cast_player_cell_portent,
    "lullaby": EnemySkillMixin._cast_lullaby,
    "oblivion_mark": EnemySkillMixin._cast_oblivion_mark,
    "redact_buff": EnemySkillMixin._cast_redact_buff,
    "core_pause": EnemySkillMixin._cast_core_pause,
    # 场
    "slow_pool": EnemySkillMixin._cast_slow_pool,
    "ink_pool": EnemySkillMixin._cast_ink_pool,
    "fog_veil": EnemySkillMixin._cast_fog_veil,
    "nightmare_patch": EnemySkillMixin._cast_nightmare_patch,
    "core_chill": EnemySkillMixin._cast_core_chill,
    "fire_seed": EnemySkillMixin._cast_fire_seed,
    "electric_stitch": EnemySkillMixin._cast_electric_stitch,
    "gift_bomb": EnemySkillMixin._cast_gift_bomb,
    "space_fold": EnemySkillMixin._cast_space_fold,
    "vine_grow": EnemySkillMixin._cast_vine_grow,
    "cool_drain": EnemySkillMixin._cast_cool_drain,
    "stair_fracture": EnemySkillMixin._cast_stair_fracture,
    "scribe_erase": EnemySkillMixin._cast_scribe_erase,
    # 范围/核心
    "core_period": EnemySkillMixin._cast_core_period,
    "core_beacon": EnemySkillMixin._cast_core_beacon,
    "core_cry": EnemySkillMixin._cast_core_cry,
    "scribe_draft": EnemySkillMixin._cast_scribe_draft,
    # 召唤
    "split_echo": EnemySkillMixin._cast_split_echo,
    "core_summon": EnemySkillMixin._cast_core_summon,
}

_SKILL_RESOLVERS: dict[str, Any] = {
    "model_push": EnemySkillMixin._skill_resolve_default_hit,
    "abyss_pull": EnemySkillMixin._skill_resolve_default_hit,
    "paper_dart": EnemySkillMixin._skill_resolve_default_hit,
    "light_trace": EnemySkillMixin._skill_resolve_default_hit,
    "mind_bite": EnemySkillMixin._skill_resolve_default_hit,
    "null_ray": EnemySkillMixin._skill_resolve_default_hit,
    "scribe_stroke": EnemySkillMixin._skill_resolve_default_hit,
    "core_period": EnemySkillMixin._skill_resolve_default_hit,
    "core_beacon": EnemySkillMixin._skill_resolve_default_hit,
    "echo_dash": EnemySkillMixin._resolve_dash,
    "return_charge": EnemySkillMixin._resolve_dash,
    "mirror_swap": EnemySkillMixin._resolve_mirror_swap,
    "fold_guard": EnemySkillMixin._resolve_fold_guard,
    "choir_guard": EnemySkillMixin._resolve_choir_guard,
    "wake_allies": EnemySkillMixin._resolve_wake_allies,
    "echo_alert": EnemySkillMixin._resolve_echo_alert,
    "shadow_step": EnemySkillMixin._resolve_shadow_step,
    "edit_heal": EnemySkillMixin._resolve_edit_heal,
    "scribe_revision": EnemySkillMixin._resolve_scribe_revision,
    "clock_drag": EnemySkillMixin._resolve_clock_drag,
    "seam_bind": EnemySkillMixin._resolve_seam_bind,
    "mislabel": EnemySkillMixin._resolve_mislabel,
    "lullaby": EnemySkillMixin._resolve_lullaby,
    "oblivion_mark": EnemySkillMixin._resolve_oblivion_mark,
    "redact_buff": EnemySkillMixin._resolve_redact_buff,
    "core_pause": EnemySkillMixin._resolve_core_pause,
    "slow_pool": EnemySkillMixin._resolve_field_only,
    "ink_pool": EnemySkillMixin._resolve_field_only,
    "fog_veil": EnemySkillMixin._resolve_field_only,
    "nightmare_patch": EnemySkillMixin._resolve_field_only,
    "core_chill": EnemySkillMixin._resolve_field_only,
    "fire_seed": EnemySkillMixin._resolve_fire_seed,
    "electric_stitch": EnemySkillMixin._resolve_electric_stitch,
    "gift_bomb": EnemySkillMixin._resolve_gift_bomb,
    "space_fold": EnemySkillMixin._resolve_field_only,
    "vine_grow": EnemySkillMixin._resolve_field_only,
    "cool_drain": EnemySkillMixin._resolve_cool_drain,
    "stair_fracture": EnemySkillMixin._resolve_stair_fracture,
    "scribe_erase": EnemySkillMixin._resolve_scribe_erase,
    "core_cry": EnemySkillMixin._resolve_core_cry,
    "scribe_draft": EnemySkillMixin._skill_resolve_default_hit,
    "split_echo": EnemySkillMixin._resolve_summon,
    "core_summon": EnemySkillMixin._resolve_summon,
}

EnemySkillMixin._SKILL_CASTERS = _SKILL_CASTERS
EnemySkillMixin._SKILL_RESOLVERS = _SKILL_RESOLVERS

from .hospital_skills import cast as _hospital_cast, resolve as _hospital_resolve
from ..data.hospital import HOSPITAL_SKILLS
for _key, *_ in HOSPITAL_SKILLS:
    _SKILL_CASTERS['hospital.'+_key] = _hospital_cast
    _SKILL_RESOLVERS['hospital.'+_key] = _hospital_resolve

from .library_skills import cast as _library_cast, resolve as _library_resolve
from ..data.library import LIBRARY_SKILLS
for _key, *_rest in LIBRARY_SKILLS:
    _SKILL_CASTERS['library.'+_key] = _library_cast
    _SKILL_RESOLVERS['library.'+_key] = _library_resolve

# 漏字者的「吞音」：Python 定义技能（规格 §7.3），解析器在 core/tamper_risks.py。
from .tamper_risks import register_omission_skill as _register_omission_skill
_register_omission_skill()
