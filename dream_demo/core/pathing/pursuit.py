"""异象寻路与追踪状态机：发现→实时规划、丢失→沿计划、到终点→游荡。

异象的移动候选由这里给出（``_enemy_move_candidates``，供 enemies.py 的
``_enemy_move_step`` 消费），全部走与玩家同源的 8 向 A*（:mod:`.astar`，
经 :class:`.routes.PathMixin.path_to` 封装）：

- **看见玩家**（``_enemy_turns`` 的感知段）：立即以玩家当前位置为终点
  规划最短路径（``_plan_chase``）——实时追击，玩家每动一步都会在下一次
  感知时重规划；
- **丢失视野**：不再重规划，按 ``path_plan`` 里剩余的路径继续走向最后一次
  目击处（超过 LOST_TARGET_TURNS 降级为怀疑，但计划不清）；
- **走到计划终点**（通常是目击处）仍没发现目标：转入**游荡**——随机挑一个
  附近的开放格走过去，到了再挑下一个，直到重新看见玩家；
- **中途重新发现**：感知段清掉游荡标记并重规划，立刻改道。

计划被别的生物/坍塌挡住时按原终点重算一次；重算仍不可达就放弃计划转为
游荡。从未获得计划的异象保持旧的贪心三向行为（未察觉/怀疑的「无脑靠近」
留在 ``_greedy_candidates``）。纸鱼另有亲液 A*（``_liquid_path``）：只沿
连续液面规划，绕得开墙与干地；液面无路时才退回旧三向筛选。
"""

from __future__ import annotations

import random
import zlib

from ...data.anomaly_skills import bindings_for, effective_skill_def
from ...materials import DOOR_KINDS
from ..roles import ROLE_FRONT, role_for, side_of

# §22 B：各类证据的有效期（世界回合，不按函数调用次数）。
VISUAL_MEMORY_TURNS = 4
VISUAL_MEMORY_TURNS_HUNTER = 6
INVESTIGATION_TURNS = 12
INVESTIGATION_TURNS_HUNTER = 20
INVESTIGATION_SAFETY_LIMIT = 128

# §5.1 距离带：射手优先停在真实射程内、退得开的格，而不是永远贴到玩家脸上。
# 只登记明确以远程为角色的种类；其余近战保持“最短合法接近”。
#
# 登记依据（2026-10-22 实测，不是拍脑袋）：把某个种类单独放在空场里，
# 逐个调用它绑定的真实 caster（`_SKILL_CASTERS`），返回 None 即「这个位置上
# 没有一张能出的牌」。逐种类扫 d=1..8：
#   · 这 13 个种类在 d=1 **一张牌都出不了**（射线/瞄准类技能的下限是 2），
#     它们贴上来只会普攻，等于把远程角色演成近战；
#     其中 `faceless_editor` 不进表：它绑了 `edit_heal`，角色判定里
#     「辅助」优先于「后排」（见 `core/roles.py`），登记它只会在它的
#     唯一攻击技上多套一层换线门控，对角色系统没有增益。
#   · 其余 12 个的合法窗口交集正好是 [3, 6]：最晚开张的是 `sleepless_watch`
#     （d=3），最早收摊的是 `return_runner`/`thought_worm`/`unopened_gift`
#     （d=7 归零）。所以全表统一取交集 `(3, 6)`，不按种类各写一个值——
#     各写各的只会让下一个人重新猜一遍「这个 2 和那个 3 到底谁对」。
#
# 被否掉的口径（都可查）：① 按 `max_range` 判远程——73 个技能全是 8，全员命中；
# ② 按「绑定里远程形状过半」——`锁定局部范围` 这一个兜底形状就占 29/73，
# 判出 50 个候选，等于没有角色；③ 按「有没有射线形状」——`mirror_swap`
# 这类位移技会让判据漏掉真正的后排。只有「d=1 出不了牌」是机制层面的硬事实。
RANGED_BAND_MIN = 3
RANGED_BAND_MAX = 6
RANGED_DISTANCE_BANDS = {
    "anomaly.abyss_ruler": (RANGED_BAND_MIN, RANGED_BAND_MAX),
    "anomaly.backlit_reader": (RANGED_BAND_MIN, RANGED_BAND_MAX),
    "anomaly.echo_scribe": (RANGED_BAND_MIN, RANGED_BAND_MAX),
    "anomaly.faceless_watchman": (RANGED_BAND_MIN, RANGED_BAND_MAX),
    "anomaly.folded_room": (RANGED_BAND_MIN, RANGED_BAND_MAX),
    "anomaly.mirror_attendant": (RANGED_BAND_MIN, RANGED_BAND_MAX),
    "anomaly.null_witness": (RANGED_BAND_MIN, RANGED_BAND_MAX),
    "anomaly.return_runner": (RANGED_BAND_MIN, RANGED_BAND_MAX),
    "anomaly.silent_mirror": (RANGED_BAND_MIN, RANGED_BAND_MAX),
    "anomaly.sleepless_watch": (RANGED_BAND_MIN, RANGED_BAND_MAX),
    "anomaly.thought_worm": (RANGED_BAND_MIN, RANGED_BAND_MAX),
    "anomaly.unopened_gift": (RANGED_BAND_MIN, RANGED_BAND_MAX),
}

# §5.1 撤退位（2026-10-22）：把「退一步再开火」从登记种类推广到所有真远程。
# 依据是硬事实：射线类技能的距离下限是 2（`_sk_player_line`），本体一旦贴到
# 玩家身上，所有射线同时非法，而旧代码没有任何分支会把它挪开——它只能在
# 原地普攻或停住。这里给它一个「退一步就重新有牌可打」的落点。
RETREAT_SLOT_RANGE_MIN = 2      # 与射线技能的距离下限一致，不另设门槛
RETREAT_SLOT_MAX_DIST = 3       # 退太远会丢掉本回合的行动价值
RETREAT_SLOT_MIN_RANGE = 3      # 只认真正以远程为主的技能（max_range ≥ 3）

# §5.1 封路位（2026-10-22）：抢不到贴身位时，去占玩家附近唯一的窄口。
# 只认 `_sk_is_choke` 判定过的门洞／一格走廊，只占一格，不猜玩家要往哪跑。
BLOCK_SLOT_LOOK_RADIUS = 3
BLOCK_SLOT_TRIAL_CELLS = 4

# §5.1 支援目的地区域：这些技能要「站到够得着同伴的位置」才生效。
# 需求谓词直接复用施法入口的同一套合法条件，不新增机制。
_SUPPORT_SKILL_IDS = ("edit_heal", "wake_allies", "echo_alert")
# 落点候选只试最近这几个，避免每次决策都全图重算。
_SUPPORT_TRIAL_CELLS = 6


class PursuitMixin:
    # ------------------------------------------------------------------
    # 感知与规划
    # ------------------------------------------------------------------
    def _enemy_sees_player(self, enemy) -> bool:
        """异象此刻是否看得见玩家（曼哈顿距离 ≤ 视野且视线无遮挡）。

        §12 H2 匿踪：只遮蔽视觉，不抹掉声源或最后目击点。
        """
        if getattr(self, "vanish_turns", 0) > 0:
            return False
        return self.can_see(enemy, self.player.x, self.player.y)

    def _attack_slot_claims(self, enemy) -> set[tuple[int, int]]:
        """§9 短时预约：本回合内其他近战异象已经选定的攻击格。

        只约束当前这一回合的站位选择，不写进存档，也不把整条长路径占住。
        """
        claims = getattr(self, "nav_slot_claims", None) or {}
        return {(int(cell[0]), int(cell[1]))
                for eid, cell in claims.items() if eid != str(enemy.id)}

    def _claim_attack_slot(self, enemy, cell) -> None:
        claims = getattr(self, "nav_slot_claims", None)
        if claims is None:
            claims = self.nav_slot_claims = {}
        claims[str(enemy.id)] = (int(cell[0]), int(cell[1]))

    def _free_melee_slot(self, enemy, tx: int, ty: int,
                         claims) -> tuple[int, int] | None:
        """§5.1 近战包围位：目标格周围按「离自己最近」找一个未被预约的攻击格。

        空格与同伴预约都算占用；没有合法空位时返回 ``None``，让追猎退回排队，
        不凭空造出安全格，也不要求所有同伴同时绕大圈。

        **侧翼协作（2026-10-22）**：``front`` 角色的异象在同一目标周围优先选
        「这一侧还没人」的格。只把「最近」和「不同侧」两件事叠起来做：先排除
        已被同伴占掉的方位桶，再在剩下的里取最近。无技能的普通异象
        （``ROLE_NONE``）不参与，保持原来只挑最近空位的行为。
        """
        spots = []
        for order, (dx, dy) in enumerate(self._NAV_NEIGHBORS):
            pos = (tx + dx, ty + dy)
            if not (0 <= pos[0] < self.width and 0 <= pos[1] < self.height):
                continue
            if self.cell(*pos).solid:
                continue
            occupant = self.entity_at(*pos)
            if occupant is not None and occupant is not enemy:
                continue
            if pos in claims:
                continue
            spots.append((max(abs(pos[0] - enemy.x), abs(pos[1] - enemy.y)),
                          order, pos))
        if not spots:
            return None
        if len(spots) > 1 and role_for(getattr(enemy, "catalog_id", "")) == ROLE_FRONT:
            spots = self._spread_current_sides(enemy, tx, ty, spots, claims)
        spots.sort()
        return spots[0][2]

    def _spread_current_sides(self, enemy, tx: int, ty: int, spots, claims):
        """§5.1 侧翼协作：把已被同伴占掉的方位桶从候选里摘掉。

        「占掉」取两种证据：本回合的攻击格预约，以及已经站在目标周围且属于
        失控意识的同伴。摘完为空就原样返回（宁可同侧排队，也不能因此放弃攻击位）。
        """
        taken = {side_of((tx, ty), cell) for cell in claims}
        for dx, dy in self._NAV_NEIGHBORS:
            pos = (tx + dx, ty + dy)
            occupant = self.entity_at(*pos)
            if (occupant is not None and occupant is not enemy
                    and getattr(occupant, "relation", "") == "失控意识"):
                taken.add(side_of((tx, ty), pos))
        if not taken:
            return spots
        free = [item for item in spots if side_of((tx, ty), item[2]) not in taken]
        return free or spots

    def _reserve_melee_slot(self, enemy, plan, tx: int, ty: int) -> list:
        """近战斗争目的地：多个异象盯同一目标时分散到不同的贴身高。

        计划终点就是目标格（玩家／最后目击点）时，攻击位取计划倒数第二格；
        该格已被本回合同伴预约就改打另一条合法包围位并重规划。已经贴在目标
        旁边的异象不为了「分散」再挪开，避免在玩家脸上来回换格。
        """
        if not plan:
            return plan
        ends_on_target = plan[-1] == (tx, ty)
        if ends_on_target and len(plan) < 2:
            self._claim_attack_slot(enemy, (enemy.x, enemy.y))
            return plan
        attack = plan[-2] if ends_on_target else plan[-1]
        claims = self._attack_slot_claims(enemy)
        if attack not in claims:
            self._claim_attack_slot(enemy, attack)
            return plan
        if not ends_on_target:
            # 目的地不是目标格本身（调查点等）：让路交给 §5.3 的等待／侧移。
            return plan
        slot = self._free_melee_slot(enemy, tx, ty, claims)
        if slot is None or slot == (enemy.x, enemy.y):
            return plan
        alt = self.path_to(slot[0], slot[1], start=(enemy.x, enemy.y),
                           portents=enemy.portents)
        if not alt:
            return plan
        self._claim_attack_slot(enemy, slot)
        return alt

    def _queued_approach(self, enemy, target_x: int, target_y: int) -> list[tuple[int, int]]:
        """§5.3 窄通道显式排队：同伴的身体挡住唯一通路时，先站到它身后。

        实体感知寻路判为不可达只有两种可能：地形真过不去，或者被同伴的肉体
        堵住。再用「忽略所有生物」的地形口径试一次：也走不通就是真的不可达，
        返回空表让调用方按被困处理；走得通就说明挡路的只是身体，于是沿地形
        路径走到第一个被占的格子之前停下，把这个空格当本回合的目的地。
        排队位是图里真实存在、并用同一套 A* 重新验证过的合法空格，不凭空
        造格，也不硬穿同伴。
        """
        terrain = self.path_to(target_x, target_y, start=(enemy.x, enemy.y),
                               portents=enemy.portents, known_cells=set())
        if not terrain:
            return []
        pos = (enemy.x, enemy.y)
        for cell in terrain:
            occupant = self.entity_at(*cell)
            if occupant is not None and occupant is not enemy:
                break
            if not self._enemy_step_passable(enemy, cell):
                return []
            pos = cell
        else:
            return terrain
        if pos == (enemy.x, enemy.y):
            return []
        return self.path_to(pos[0], pos[1], start=(enemy.x, enemy.y),
                            portents=enemy.portents)

    def _enemy_step_cost(self, enemy):
        """§5.2：已知危险格加权；未知区域不凭空知道。"""
        hazardous = {"酸液", "燃油", "熔念金属", "液氮", "液氦"}
        def cost(x: int, y: int) -> int:
            cell = self.cell(x, y)
            if cell.flame and self.can_see(enemy, x, y):
                return 3
            if cell.liquid > 0 and cell.liquid_kind in hazardous and self.can_see(enemy, x, y):
                return 3
            return 1
        return cost

    def _breach_capable(self, enemy) -> bool:
        return bool(self._enemy_skill_spec(enemy, "wall_break"))

    def _breach_passable(self, enemy):
        def passable(x: int, y: int) -> bool:
            cell = self.cell(x, y)
            if not cell.solid or cell.wall_kind in DOOR_KINDS:
                return True
            return self._enemy_can_break_wall(enemy, x, y)
        return passable

    def _breach_step_cost(self, enemy):
        base = self._enemy_step_cost(enemy)
        def cost(x: int, y: int) -> int:
            cell = self.cell(x, y)
            breach = cell.solid and cell.wall_kind not in DOOR_KINDS
            return (1 if breach else 0) + base(x, y)
        return cost

    def _plan_chase(self, enemy, target_x: int, target_y: int) -> list[tuple[int, int]]:
        """以 (target_x, target_y) 为终点重规划追踪路径，写回实体并返回。

        规划即「获得新目标」：清掉游荡标记。空表表示不可达（计划被清空，
        调用方会回退到贪心/游荡）。近战者按 §5.1 分散到不同包围位，
        后排不会反复抢同一个已被同伴占住的攻击格；只剩同伴身体挡路时
        按 §5.3 排到它身后，而不是原地冻住。
        """
        plan = self.path_to(
            target_x,
            target_y,
            start=(enemy.x, enemy.y),
            portents=enemy.portents,
            step_cost=self._enemy_step_cost(enemy),
        )
        if not plan and self._breach_capable(enemy):
            # 普通路不可达时才考虑真实破障动作边：墙体进入路径，但进入墙
            # 本身要额外花一步，执行层再调用 destroy_wall。
            plan = self.path_to(
                target_x, target_y, start=(enemy.x, enemy.y),
                portents=enemy.portents,
                passable_override=self._breach_passable(enemy),
                step_cost=self._breach_step_cost(enemy),
            )
        if not plan:
            plan = self._queued_approach(enemy, target_x, target_y)
        if not RANGED_DISTANCE_BANDS.get(getattr(enemy, "catalog_id", "")):
            plan = self._reserve_melee_slot(enemy, plan, target_x, target_y)
        enemy.path_plan = plan
        enemy.plan_index = 0
        enemy.wandering = False
        return plan

    def _ally_in_influence(self, enemy, ally, radius: int) -> bool:
        """本体此刻能否影响到同伴：与 ``_sk_allies_near`` 同一口径（射程＋视线）。"""
        if max(abs(ally.x - enemy.x), abs(ally.y - enemy.y)) > radius:
            return False
        return self._has_line_of_sight(enemy.x, enemy.y, ally.x, ally.y)

    def _support_need_for(self, skill_id: str, enemy, ally, player_cell) -> bool:
        """需求谓词：与对应施法入口对同一同伴的判断保持一致。"""
        if skill_id == "edit_heal":
            return (ally.anomaly_kind == enemy.anomaly_kind
                    and 0 < ally.integrity * 2 <= self._sk_enemy_max(ally))
        if skill_id == "wake_allies":
            return ally.alert_state == "追踪" and "sk_guidance" not in ally.portents
        # echo_alert：同伴还没有本体的目击；本体看不见玩家时不播报旧坐标。
        return not (ally.alert_state == "追踪"
                    and (ally.last_seen_x, ally.last_seen_y) == player_cell)

    def _support_need(self, enemy):
        """返回 ``(同伴, 射程, 技能id)``：走过去才帮得上忙的支援需求。

        同伴已经在影响范围内就无需走位；需求消失（治疗预算为空、已被指引、
        已知玩家位置）时返回 None，调用方按原来的证据目标行动。
        """
        bindings = bindings_for(getattr(enemy, "catalog_id", ""))
        if not bindings or enemy.alert_state == "未察觉":
            return None
        if self._skill_channeling(enemy):
            return None
        st = self._skill_state(enemy)
        player_cell = (self.player.x, self.player.y)
        for binding in bindings:
            skill_id = binding.skill_id
            if skill_id not in _SUPPORT_SKILL_IDS:
                continue
            if skill_id == "edit_heal" and int(st.get("heal_budget", 0)) <= 0:
                continue
            if skill_id == "echo_alert" and not self._enemy_sees_player(enemy):
                continue
            radius = int(effective_skill_def(skill_id, enemy.catalog_id).max_range)
            for other in self.enemies:
                if other is enemy or other.integrity <= 0:
                    continue
                if other.relation != "失控意识":
                    continue
                if self._ally_in_influence(enemy, other, radius):
                    continue
                if not self._support_need_for(skill_id, enemy, other, player_cell):
                    continue
                return other, radius, skill_id
        return None

    def _hold_slot_claims(self, enemy) -> set[tuple[int, int]]:
        """本回合已被别人占用的**非攻击格**（候位／支援位／撤退位／距离带／封路位）。

        §9 的「短时预约」原来只管近战攻击格，于是一件只发生在站位上的事没被
        约束：两个同伴同一回合算出同一个支援位或同一条距离带落点，走过去互相
        顶着；或者一个占住了撤退位，另一个把它算成自己的后撤落点。
        这里把「本回合谁站哪」统一成一张表（与攻击格一并排除），
        与 ``nav_slot_claims`` 同生命周期：每回合清空、不写存档。
        """
        hold = getattr(self, "nav_hold_claims", None) or {}
        taken = {(int(c[0]), int(c[1]))
                 for eid, c in hold.items() if eid != str(enemy.id)}
        taken |= self._attack_slot_claims(enemy)
        return taken

    def _claim_hold_slot(self, enemy, cell) -> None:
        claims = getattr(self, "nav_hold_claims", None)
        if claims is None:
            claims = self.nav_hold_claims = {}
        claims[str(enemy.id)] = (int(cell[0]), int(cell[1]))

    def _support_cells(self, enemy, ally, radius: int) -> list[tuple[int, int]]:
        """同伴周围「站上去就够得着」的合法格，按离本体近到远取前若干个。

        已被同伴预约的站位（含攻击格）直接跳过——这是「多支援抢位」的实际
        解法：不是随机化，而是先到先得，第二个支援者拿次近的合法格。
        """
        taken = self._hold_slot_claims(enemy)
        scored = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                x, y = ally.x + dx, ally.y + dy
                if not (0 <= x < self.width and 0 <= y < self.height):
                    continue
                if max(abs(dx), abs(dy)) > radius:
                    continue
                if (x, y) in taken:
                    continue
                if self.cell(x, y).solid or not self._enemy_step_passable(enemy, (x, y)):
                    continue
                if not self._has_line_of_sight(x, y, ally.x, ally.y):
                    continue
                scored.append(((x, y), max(abs(x - enemy.x), abs(y - enemy.y))))
        scored.sort(key=lambda item: (item[1], item[0]))
        return [cell for cell, _ in scored[:_SUPPORT_TRIAL_CELLS]]

    def _plan_support(self, enemy) -> list[tuple[int, int]]:
        """§5.1 支援走位：走向最近的可影响格；没有合法落点就交回原目标。"""
        need = self._support_need(enemy)
        if need is None:
            return []
        ally, radius, skill_id = need
        for cell in self._support_cells(enemy, ally, radius):
            plan = self.path_to(
                cell[0], cell[1], start=(enemy.x, enemy.y),
                portents=enemy.portents,
                step_cost=self._enemy_step_cost(enemy))
            if plan and self._enemy_step_passable(enemy, plan[0]):
                enemy.path_plan, enemy.plan_index = plan, 0
                enemy.wandering = False
                self._claim_hold_slot(enemy, cell)
                # 走位理由留在状态里，供 §11.3 的调试原因链读取。
                self._skill_state(enemy)["support_for"] = {
                    "ally_id": ally.id, "skill_id": skill_id, "cell": list(cell),
                }
                return plan
        return []

    def _is_hunter(self, enemy) -> bool:
        return getattr(enemy, "trait", "") in ("tracker", "paper_fold")

    def _visual_memory_turns(self, enemy) -> int:
        return VISUAL_MEMORY_TURNS_HUNTER if self._is_hunter(enemy) else VISUAL_MEMORY_TURNS

    def _investigation_retention(self, enemy) -> int:
        return (INVESTIGATION_TURNS_HUNTER if self._is_hunter(enemy)
                else INVESTIGATION_TURNS)

    def _remember_investigation(self, enemy, x: int, y: int,
                                source: str, category: str,
                                *, heard_at: int | None = None) -> None:
        """登记／刷新一条调查任务（按地点＋来源去重）。

        同一静态诱饵持续响只更新时间与保存期限，不重复插入；已经查验过的
        同一地点不会被重复响声重新激活（真正的新声源会带来新地点）。
        """
        if x < 0 or y < 0 or not (0 <= x < self.width and 0 <= y < self.height):
            return
        now = self.time if heard_at is None else int(heard_at)
        tasks = enemy.investigation_tasks
        for task in tasks:
            if (task.get("x") == x and task.get("y") == y
                    and task.get("source") == source):
                task["time"] = max(int(task.get("time", 0)), now)
                task["expires"] = max(int(task.get("expires", 0)),
                                      now + self._investigation_retention(enemy))
                task["category"] = category
                task["unreachable"] = False
                return
        tasks.append({
            "x": int(x), "y": int(y), "source": source, "category": category,
            "time": now, "expires": now + self._investigation_retention(enemy),
            "tried": False, "unreachable": False,
        })
        if len(tasks) > INVESTIGATION_SAFETY_LIMIT:
            # 只在地点/来源去重后的极端堆积下裁掉最旧条目；不按条数静默
            # 丢弃仍在有效期内的不同路线（去重后通常远低于此上限）。
            tasks.sort(key=lambda task: int(task.get("time", 0)))
            del tasks[:len(tasks) - INVESTIGATION_SAFETY_LIMIT]

    def _prune_investigations(self, enemy) -> None:
        now = self.time
        enemy.investigation_tasks = [
            task for task in enemy.investigation_tasks
            if int(task.get("expires", 0)) >= now
        ]

    def _investigation_path(self, enemy, x: int, y: int):
        """到调查点的合法路径；目标格不可踩时改试最近的四邻观察位。"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return None
        candidates = [(x, y)]
        if self.cell(x, y).solid:
            candidates = [(x + dx, y + dy) for dx, dy in
                          ((1, 0), (-1, 0), (0, 1), (0, -1))]
        for tx, ty in candidates:
            if not (0 <= tx < self.width and 0 <= ty < self.height):
                continue
            if self.cell(tx, ty).solid:
                continue
            if (enemy.x, enemy.y) == (tx, ty):
                return [], (tx, ty)
            plan = self.path_to(tx, ty, start=(enemy.x, enemy.y),
                                portents=enemy.portents)
            if plan:
                return plan, (tx, ty)
        return None

    def _next_investigation(self, enemy):
        """最近的、仍有效且未尝试的调查任务（真实路径耗时，非直线）。"""
        self._prune_investigations(enemy)
        revision = int(getattr(self, "topology_revision", 0))
        for task in enemy.investigation_tasks:
            # 旧路线被墙挡下后挂起；只有门／墙拓扑真的变了才重新尝试，
            # 不因每回合重算寻路而反复失败（docs 261022 §8）。
            if task.get("unreachable") and int(task.get("topology", 0)) != revision:
                task["unreachable"] = False
        best = None
        best_key = None
        for task in enemy.investigation_tasks:
            if task.get("tried") or task.get("unreachable"):
                continue
            x, y = int(task.get("x", -1)), int(task.get("y", -1))
            if (enemy.x, enemy.y) == (x, y):
                task["tried"] = True
                continue
            found = self._investigation_path(enemy, x, y)
            if found is None:
                task["unreachable"] = True
                task["topology"] = revision
                continue
            plan, approach = found
            task["approach_x"], task["approach_y"] = approach
            key = (len(plan), -int(task.get("time", 0)),
                   str(task.get("source", "")), x, y)
            if best_key is None or key < best_key:
                best, best_key = task, key
        return best

    def _visual_memory_target(self, enemy):
        """仍然有效的最后目击点；过期、无记忆或已站在该点则返回 None。"""
        if enemy.last_seen_x < 0:
            return None
        if (enemy.x, enemy.y) == (enemy.last_seen_x, enemy.last_seen_y):
            return None
        seen_at = int(getattr(enemy, "last_seen_time", -1))
        if seen_at >= 0 and self.time - seen_at > self._visual_memory_turns(enemy):
            return None
        return enemy.last_seen_x, enemy.last_seen_y

    def _enemy_chase_target(self, enemy):
        """异象此刻有合法证据的目标格；没有任何证据时返回 ``None``。

        优先级：仍然有效的最后目击点 → 最近的未完成调查任务。绝不回退到
        玩家实时坐标：没有看见、没有听见、没有收到传信时只能游荡。
        """
        target = self._visual_memory_target(enemy)
        if target is not None:
            return target
        task = self._next_investigation(enemy)
        if task is not None:
            return (int(task.get("approach_x", task["x"])),
                    int(task.get("approach_y", task["y"])))
        return None

    def _check_investigation_completion(self, enemy) -> None:
        """从合法位置看清调查点且没发现目标时，结束该任务。

        只在当前没有看见玩家时结算；被烟、高草或墙挡住的格子不算「看过」。
        """
        if self._enemy_sees_player(enemy):
            return
        for task in enemy.investigation_tasks:
            if task.get("tried"):
                continue
            x, y = int(task.get("x", -1)), int(task.get("y", -1))
            if (enemy.x, enemy.y) == (x, y):
                task["tried"] = True
            elif self.can_see(enemy, x, y):
                task["tried"] = True

    # ------------------------------------------------------------------
    # 移动候选
    # ------------------------------------------------------------------
    def _enemy_step_passable(self, enemy, position: tuple[int, int]) -> bool:
        """这一步现在是否真的迈得出去（门算可通行：踩上会开门）。"""
        x, y = position
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        cell = self.cell(x, y)
        if cell.solid and cell.wall_kind not in DOOR_KINDS:
            return False
        if (x, y) == (self.player.x, self.player.y):
            return False
        return self.entity_at(x, y) is None

    _NAV_NEIGHBORS = ((0, -1), (1, 0), (0, 1), (-1, 0),
                      (1, -1), (1, 1), (-1, 1), (-1, -1))

    def _blocker_is_leaving(self, blocker) -> bool:
        """同伴是否只是路过：有剩余计划，且没有站定蓄力／施法。"""
        if getattr(blocker, "aoe_charge", 0.0) > 0:
            return False
        if blocker.active_skill_state.get("pending"):
            return False
        plan = blocker.path_plan
        return bool(plan and blocker.plan_index < len(plan))

    def _nav_sidestep(self, enemy, target_x: int, target_y: int, *,
                      liquid: bool = False):
        """计划步被同伴占住时，换一个仍能走到目标的相邻站位。

        返回的路径首格就是这一步该迈出的替代格；没有任何可达替代时返回
        ``None``。连续无进展时优先避开两步前的落点，避免 A→B→A 往返
        （方案 §5.3 第 4 条）。
        """
        recent = [tuple(cell) for cell in enemy.nav_recent if len(cell) == 2]
        backtrack = recent[-2] if len(recent) >= 2 and recent[-1] == (enemy.x, enemy.y) else None
        best = None
        for order, (dx, dy) in enumerate(self._NAV_NEIGHBORS):
            pos = (enemy.x + dx, enemy.y + dy)
            if not self._enemy_step_passable(enemy, pos):
                continue
            if liquid:
                if self.cell(*pos).liquid <= 0:
                    continue
                plan = self._liquid_path(enemy, target_x, target_y, start=pos)
                if not plan and pos != (target_x, target_y):
                    continue
            elif pos == (target_x, target_y):
                plan = []
            else:
                plan = self.path_to(target_x, target_y, start=pos,
                                    portents=enemy.portents)
                if not plan:
                    continue
            key = (len(plan), 1 if pos == backtrack else 0, order)
            if best is None or key < best[0]:
                best = (key, [pos] + plan)
        return None if best is None else best[1]

    def _mutual_block(self, enemy, blocker) -> bool:
        """§5.3 相向卡门：对方下一步也想踩进我这一格。"""
        if getattr(blocker, "aoe_charge", 0.0) > 0:
            return False
        if blocker.active_skill_state.get("pending"):
            return False
        plan = blocker.path_plan
        if not plan or blocker.plan_index >= len(plan):
            return False
        return tuple(plan[blocker.plan_index]) == (enemy.x, enemy.y)

    def _nav_alt_for_blocked_step(self, enemy, step, target, *, liquid=False):
        """计划步被占时先等一回合让路，再换站位；返回替代路径或 ``None``。"""
        blocker = self.entity_at(*step)
        if blocker is None:
            return None
        blocked = [step[0], step[1]]
        if enemy.nav_blocked != blocked:
            # 堵点换了：新的同伴值得重新判断一次是否只是路过。
            enemy.nav_waited = False
            enemy.nav_wait_since = -1
        enemy.nav_blocked = blocked
        if (enemy.nav_stall < 2 and not enemy.nav_waited
                and self._blocker_is_leaving(blocker)):
            # 同伴只是路过：先等一个正常移动耗时（本回合不出手），
            # 下次仍被挡再侧移到其他合法站位（§5.3 第 1 条）。
            enemy.nav_waited = True
            return []
        if self._mutual_block(enemy, blocker):
            # 双方都想走对方那格：等待较久者保留优先通行，较晚到达者先让。
            # 同一时刻到达时按实体 id 稳定决胜，避免永远由出生顺序靠前者占先。
            if enemy.nav_wait_since < 0:
                enemy.nav_wait_since = int(self.time)
            since = (int(blocker.nav_wait_since)
                     if blocker.nav_wait_since >= 0 else int(self.time))
            senior = (enemy.nav_wait_since, str(enemy.id)) < (since, str(blocker.id))
            if senior and not enemy.nav_waited and self.time - enemy.nav_wait_since < 2:
                # 让先到者继续等待：对方按同一规则会让路；等待两回合后
                # 即使对方不动也自行换位，避免互相僵死。
                enemy.nav_waited = True
                return []
        return self._nav_sidestep(enemy, target[0], target[1], liquid=liquid)

    def _ranged_position_step(self, enemy, target, band):
        """§5.1：射手的距离带站位。返回 ``None`` 表示照常接近，``[]`` 表示
        已在合适位置按兵不动，``[step]`` 表示先退一步拉开距离。

        §8.3：同伴挡在射线上，或同一位置连续两次被同一方向躲开时，改为
        横移换一条合法射击线；找不到就原地等同伴移开，不隔人开火。

        只改变站位，不读玩家未提交输入，也不延长任何技能射程；没有实时
        视线时退回普通的目击点追击。
        """
        if not self._enemy_sees_player(enemy):
            return None
        lo, hi = band
        tx, ty = target
        dist = max(abs(enemy.x - tx), abs(enemy.y - ty))
        aimed = self._has_line_of_sight(enemy.x, enemy.y, tx, ty)
        blocked = self._friendly_line_blocker(
            enemy, enemy.x, enemy.y, tx, ty) is not None
        relocate = blocked or self._recent_whiff_any(enemy)
        if lo <= dist <= hi and aimed and not relocate:
            return []
        if dist > hi:
            return None
        toward = (0 if tx == enemy.x else (1 if tx > enemy.x else -1),
                  0 if ty == enemy.y else (1 if ty > enemy.y else -1))
        back = (-toward[0], -toward[1])
        taken = self._hold_slot_claims(enemy)
        best = None
        for order, (dx, dy) in enumerate(self._NAV_NEIGHBORS):
            if relocate and (dx, dy) in (toward, back):
                continue  # 换线只走横移／斜移，不沿原来的射线进退
            pos = (enemy.x + dx, enemy.y + dy)
            if not self._enemy_step_passable(enemy, pos):
                continue
            if pos in taken:
                # 这条距离带落点已被同伴预约：拿次优的一格，别两个人并排挤。
                continue
            if not self._has_line_of_sight(pos[0], pos[1], tx, ty):
                continue
            nd = max(abs(pos[0] - tx), abs(pos[1] - ty))
            if relocate:
                clear = self._friendly_line_blocker(
                    enemy, pos[0], pos[1], tx, ty) is None
                key = (0 if clear else 1, 0 if lo <= nd <= hi else 1,
                       abs(nd - dist), order)
            else:
                if nd <= dist:
                    continue
                key = (0 if nd <= hi else 1, -min(nd, hi), order)
            if best is None or key < best[0]:
                best = (key, pos)
        if best is None:
            return None
        self._claim_hold_slot(enemy, best[1])
        return [best[1]]

    def _off_cooldown_ranged_skills(self, enemy) -> list:
        """当前不在 CD、射程 ≥ ``RETREAT_SLOT_MIN_RANGE`` 的技能（真远程）。"""
        out = []
        for binding in bindings_for(getattr(enemy, "catalog_id", "")):
            skill = effective_skill_def(binding.skill_id, enemy.catalog_id)
            if int(getattr(skill, "max_range", 0) or 0) < RETREAT_SLOT_MIN_RANGE:
                continue
            if enemy.skill_clocks.get(skill.skill_id, 0) > 0:
                continue
            out.append(skill)
        return out

    def _retreat_slot_step(self, enemy) -> list[tuple[int, int]] | None:
        """§5.1 撤退位：贴脸时退一格，让射线技能重新合法。

        为什么需要：射线技能的距离下限是 2（``EnemySkillMixin._sk_player_line``），
        本体贴到玩家身上（切比雪夫 ≤ 1）时**所有射线同时非法**，而旧代码没有
        任何分支会把它挪开——它只能在原地普攻或停住。这不是「更聪明」，是
        「它的牌全被距离规则废掉了，却没人把它退到能出牌的格子」。

        只有三条同时成立才动，避免变成隐式后撤：
        1. 此刻**看得见**玩家（不看旧证据转身）；
        2. 身上确有一个射程 ≥ 3、不在 CD 的技能（退了才有用）；
        3. 玩家就在贴身距离内。

        落点：相邻可通行格，仍有视线、距离落在 2—3；优先 2 格（多数技能射程
        下限更高时仍可再退），其次避开同伴预约的攻击格，最后按固定邻域顺序。
        找不到合法落点返回 ``None``，交回原有近战／压上逻辑，不朝墙反复蹭。
        """
        if getattr(enemy, "trait", "") == "liquid_swimmer":
            return None  # 亲液种不能上岸，撤退位不适用
        if not self._enemy_sees_player(enemy):
            return None
        if not self._off_cooldown_ranged_skills(enemy):
            return None
        px, py = self.player.x, self.player.y
        if max(abs(enemy.x - px), abs(enemy.y - py)) > 1:
            return None
        taken = self._hold_slot_claims(enemy)
        best = None
        for order, (dx, dy) in enumerate(self._NAV_NEIGHBORS):
            pos = (enemy.x + dx, enemy.y + dy)
            if not self._enemy_step_passable(enemy, pos):
                continue
            nd = max(abs(pos[0] - px), abs(pos[1] - py))
            if not (RETREAT_SLOT_RANGE_MIN <= nd <= RETREAT_SLOT_MAX_DIST):
                continue
            if not self._has_line_of_sight(pos[0], pos[1], px, py):
                continue
            if pos in taken:
                continue
            key = (abs(nd - RETREAT_SLOT_RANGE_MIN), order)
            if best is None or key < best[0]:
                best = (key, pos)
        if best is None:
            return None
        self._claim_hold_slot(enemy, best[1])
        return [best[1]]

    def _block_slot_step(self, enemy) -> list[tuple[int, int]] | None:
        """§5.1 封路位：抢不到贴身位时，去占玩家附近唯一的窄口。

        触发条件（全部满足才动，能打就一定先打）：
        1. 看得见玩家，且距离 ≤ ``BLOCK_SLOT_LOOK_RADIUS``；
        2. 本回合**没有**可用贴身攻击位（``_free_melee_slot`` 为空）——
           否则攻击优先，不为堵门放弃一次攻击；
        3. 玩家周围 ``BLOCK_SLOT_LOOK_RADIUS`` 内存在一个空格窄口
           （``_sk_is_choke``：拿掉这格后四周接不回来），且本回合没被同伴占。

        只占一格、只用已存在的格子、不预测玩家要往哪跑；找不到就返回
        ``None``，退回原有的排队／追击，不制造「所有人堵一个门」的僵局。
        """
        if getattr(enemy, "trait", "") == "liquid_swimmer":
            return None
        if not hasattr(self, "_sk_is_choke"):
            return None  # 没有技能层（纯寻路单测）时不启用
        if not self._enemy_sees_player(enemy):
            return None
        px, py = self.player.x, self.player.y
        if max(abs(enemy.x - px), abs(enemy.y - py)) > BLOCK_SLOT_LOOK_RADIUS:
            return None
        claims = self._attack_slot_claims(enemy)
        if self._free_melee_slot(enemy, px, py, claims) is not None:
            return None
        taken = self._hold_slot_claims(enemy)
        spots = []
        for dy in range(-BLOCK_SLOT_LOOK_RADIUS, BLOCK_SLOT_LOOK_RADIUS + 1):
            for dx in range(-BLOCK_SLOT_LOOK_RADIUS, BLOCK_SLOT_LOOK_RADIUS + 1):
                cell = (px + dx, py + dy)
                if cell == (enemy.x, enemy.y):
                    continue
                if not (0 <= cell[0] < self.width and 0 <= cell[1] < self.height):
                    continue
                if cell in taken or self.entity_at(*cell) is not None:
                    continue
                if not self._enemy_step_passable(enemy, cell):
                    continue
                if not self._sk_is_choke(*cell):
                    continue
                spots.append((max(abs(cell[0] - enemy.x), abs(cell[1] - enemy.y)),
                              cell))
        if not spots:
            return None
        spots.sort()
        for _, cell in spots[:BLOCK_SLOT_TRIAL_CELLS]:
            plan = self.path_to(cell[0], cell[1], start=(enemy.x, enemy.y),
                                portents=enemy.portents,
                                step_cost=self._enemy_step_cost(enemy))
            if not plan:
                continue
            self._claim_hold_slot(enemy, cell)
            enemy.path_plan, enemy.plan_index = plan, 0
            enemy.wandering = False
            return [plan[0]]
        return None

    def _enemy_move_candidates(self, enemy) -> list[tuple[int, int]]:
        """异象这一步的移动候选（按优先级）。

        沿 ``path_plan`` 走；计划走完后重新取合法证据目标（最后目击点 →
        最近调查任务）；没有任何证据就游荡。目标格只来自证据，不再回退到
        玩家实时坐标。纸鱼优先走亲液 A*，仅无液面通路时退回三向贪心。
        """
        target = self._enemy_chase_target(enemy)
        if (target is not None
                and target == (enemy.last_seen_x, enemy.last_seen_y)):
            band = RANGED_DISTANCE_BANDS.get(getattr(enemy, "catalog_id", ""))
            if band:
                choice = self._ranged_position_step(enemy, target, band)
                if choice is not None:
                    enemy.path_plan, enemy.plan_index = [], 0
                    enemy.wandering = False
                    if not choice:
                        # 守住距离带是合法的准备站位，不算 §5.3 的“无进展”。
                        enemy.nav_stall = 0
                        enemy.nav_hold = True
                    return choice
            else:
                # §5.1 撤退位：未登记距离带的真远程贴脸时先退一步（见方法注释）。
                retreat = self._retreat_slot_step(enemy)
                if retreat is not None:
                    # 记下「这个动作已经退过一格」，见下面的防回蹭守卫。
                    enemy._retreat_seq = int(self.action_seq)
                    enemy.path_plan, enemy.plan_index = [], 0
                    enemy.wandering = False
                    return retreat
            if getattr(enemy, "_retreat_seq", -1) == int(self.action_seq):
                # 同一个玩家动作内只退一次：否则移动耗时短的本体会在同一拍里
                # 「退一格 → A* 又追回去」，净效果等于原地不动还白耗计划。
                enemy.path_plan, enemy.plan_index = [], 0
                enemy.nav_stall = 0
                enemy.nav_hold = True
                return []
        if enemy.trait == "liquid_swimmer" and target is not None:
            # 亲液：先沿连续液面用同一套 A* 绕路；只有无液面通路时才退回
            # 旧三向贪心（且仍不上岸），避免把“能绕通”误判成卡墙。
            plan = enemy.path_plan
            if plan and enemy.plan_index < len(plan):
                step = plan[enemy.plan_index]
                if self._enemy_step_passable(enemy, step) and self.cell(*step).liquid > 0:
                    return [step]
                if self.entity_at(*step) is not None:
                    alt = self._nav_alt_for_blocked_step(
                        enemy, step, target, liquid=True)
                    if alt is not None:
                        if not alt:
                            return []
                        enemy.path_plan, enemy.plan_index = alt, 0
                        return [alt[0]]
            path = self._liquid_path(enemy, target[0], target[1])
            if path:
                enemy.path_plan, enemy.plan_index = path, 0
                enemy.wandering = False
                return [path[0]]
            return self._greedy_candidates(enemy, target[0], target[1])
        plan = enemy.path_plan
        # 新证据到达时，旧游荡/旧目标路径不能继续把本体带向反方向。
        if (plan and target is not None
                and max(abs(plan[-1][0] - target[0]),
                        abs(plan[-1][1] - target[1])) > 1):
            plan = enemy.path_plan = []
            enemy.plan_index = 0
        if plan and enemy.plan_index < len(plan):
            step = plan[enemy.plan_index]
            if self._enemy_step_passable(enemy, step):
                return [step]
            if self.entity_at(*step) is not None:
                alt = self._nav_alt_for_blocked_step(enemy, step, plan[-1])
                if alt is not None:
                    if not alt:
                        return []
                    enemy.path_plan, enemy.plan_index = alt, 0
                    return [alt[0]]
            # 计划被挡（别的生物站进了路径等）：以原终点重算一次。
            replan = self.path_to(
                plan[-1][0], plan[-1][1],
                start=(enemy.x, enemy.y),
                portents=enemy.portents,
            )
            if replan and self._enemy_step_passable(enemy, replan[0]):
                enemy.path_plan, enemy.plan_index = replan, 0
                return [replan[0]]
            enemy.path_plan, enemy.plan_index = [], 0
            enemy.wandering = True
        elif plan:
            # 计划走到了终点也没发现目标：清掉计划，交给证据重新选择。
            enemy.path_plan, enemy.plan_index = [], 0
            enemy.wandering = True
        if target is None:
            if getattr(enemy, "trait", "") == "mirror_step":
                # 镜像侍者的位移只由玩家移动反向驱动（movement._mirror_attendants_step）；
                # 没有证据时原地自转会破坏「共享对称轴」的设计。
                return []
            # 守卫回位（docs 261022 §5.1）：暂时追丢后回原岗，不因诱声永久丢岗。
            if (getattr(enemy, "keeps_watch", False)
                    and getattr(enemy, "trait", "") != "staircase"):
                home = (getattr(enemy, "home_x", None),
                        getattr(enemy, "home_y", None))
                if None not in home and (enemy.x, enemy.y) != home:
                    plan = self.path_to(
                        home[0], home[1], start=(enemy.x, enemy.y),
                        portents=enemy.portents,
                        step_cost=self._enemy_step_cost(enemy))
                    if plan:
                        enemy.path_plan, enemy.plan_index = plan, 0
                        enemy.wandering = False
                        return [plan[0]]
            return self._wander_candidates(enemy)
        # 新证据到达：即使正在游荡也改道调查。
        enemy.wandering = False
        # §5.1 支援：本回合帮不上的同伴若走过去帮得到，先取支援位再追击。
        support = self._plan_support(enemy)
        if support:
            return [support[0]]
        # §5.1 封路位：抢不到贴身位时改堵窄口（能打则不打这条分支）。
        block = self._block_slot_step(enemy)
        if block is not None:
            return block
        plan = self._plan_chase(enemy, target[0], target[1])
        if plan:
            return [plan[0]]
        # 目标当前不可达：把对应任务标为不可达，再尝试其余任务。
        revision = int(getattr(self, "topology_revision", 0))
        for task in enemy.investigation_tasks:
            if (int(task.get("approach_x", task.get("x", -1))),
                    int(task.get("approach_y", task.get("y", -1)))) == target:
                task["unreachable"] = True
                task["topology"] = revision
        return self._wander_candidates(enemy)

    def _greedy_candidates(self, enemy, target_x: int, target_y: int) -> list[tuple[int, int]]:
        """贪心三向：直行 X → 直行 Y → 斜向，附纸鱼的亲液筛选（旧行为）。"""
        dx = 0 if enemy.x == target_x else (1 if target_x > enemy.x else -1)
        dy = 0 if enemy.y == target_y else (1 if target_y > enemy.y else -1)
        candidates = [(enemy.x + dx, enemy.y), (enemy.x, enemy.y + dy)]
        if dx and dy:
            candidates.append((enemy.x + dx, enemy.y + dy))
        if enemy.trait == "liquid_swimmer":
            in_liquid = self.cell(enemy.x, enemy.y).liquid > 0
            liquid_candidates = [
                pos
                for pos in candidates
                if 0 <= pos[0] < self.width
                and 0 <= pos[1] < self.height
                and self.cell(*pos).liquid > 0
            ]
            if in_liquid or liquid_candidates:
                # 不会主动离开液体：只沿液面移动；干燥时优先回到液体里。
                candidates = liquid_candidates
        return candidates

    def _liquid_path(self, enemy, target_x: int, target_y: int, *, start=None):
        """亲液 A*：只在连续液面上规划，绕开干燥地面与墙体死角。

        目标格必须本身是液面（干燥目标对纸鱼不可达，交给贪心原地/回液）；
        起点不在液面时同样不规划，避免从岸上凭空“游”过去。``start`` 供
        侧移试算从相邻格出发，缺省就是异象当前格。
        """
        sx, sy = (enemy.x, enemy.y) if start is None else start
        if not (0 <= target_x < self.width and 0 <= target_y < self.height):
            return []
        if self.cell(target_x, target_y).liquid <= 0:
            return []
        if self.cell(sx, sy).liquid <= 0:
            return []
        return self.path_to(
            target_x,
            target_y,
            start=(sx, sy),
            portents=enemy.portents,
            passable_extra=lambda x, y: self.cell(x, y).liquid > 0,
        )

    # ------------------------------------------------------------------
    # 游荡
    # ------------------------------------------------------------------
    def _pick_wander_target(self, enemy) -> tuple[int, int] | None:
        """游荡：在身边 6 格范围内随机挑一个开放格（确定性随机）。"""
        suffix = enemy.id.rsplit("-", 1)[-1]
        enemy_number = int(suffix) if suffix.isdigit() else zlib.crc32(enemy.id.encode("utf-8"))
        rng = random.Random(self.seed ^ (self.time * 613) ^ (enemy_number * 31) ^ enemy.wander_nonce)
        enemy.wander_nonce += 1
        for _ in range(12):
            tx = enemy.x + rng.randint(-6, 6)
            ty = enemy.y + rng.randint(-6, 6)
            if (tx, ty) == (enemy.x, enemy.y):
                continue
            if 0 <= tx < self.width and 0 <= ty < self.height and not self.cell(tx, ty).solid:
                return (tx, ty)
        return None

    def _wander_candidates(self, enemy) -> list[tuple[int, int]]:
        """游荡的一步：挑一个新目标并规划过去；哪都去不了就原地站住。

        纸鱼的亲液同样约束游荡：只走进液面相邻格；四面干燥就原地不动，
        不能因为「没有证据」而被陆地游荡带离液体（data/perception 的亲液说明）。
        """
        if enemy.trait == "liquid_swimmer":
            options = [
                (enemy.x + dx, enemy.y + dy)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                               (1, 1), (1, -1), (-1, 1), (-1, -1))
                if 0 <= enemy.x + dx < self.width and 0 <= enemy.y + dy < self.height
                and not self.cell(enemy.x + dx, enemy.y + dy).solid
                and self.entity_at(enemy.x + dx, enemy.y + dy) is None
                and self.cell(enemy.x + dx, enemy.y + dy).liquid > 0
            ]
            if not options:
                enemy.path_plan, enemy.plan_index = [], 0
                return []
            return [options[0]]
        target = self._pick_wander_target(enemy)
        if target is None:
            enemy.path_plan, enemy.plan_index = [], 0
            return []
        plan = self.path_to(*target, start=(enemy.x, enemy.y), portents=enemy.portents)
        if not plan:
            return []
        enemy.path_plan, enemy.plan_index = plan, 0
        return [plan[0]]
