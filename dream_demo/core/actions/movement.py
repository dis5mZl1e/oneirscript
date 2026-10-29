"""移动动作族：move_player/推墙/滑冰/开门/拔植物/等待。"""
from __future__ import annotations

import random
from typing import Any, Iterable

from ...i18n import tr
from ...materials import DOOR_KINDS, GAS_DEFINITIONS, TABLE_KINDS, floor_effect_for, portent_def, wall_def
from ..content import ABILITY_DEFINITIONS, ACCESSORY_SLOTS, EQUIPMENT_POOL, EVENT_INSIGHT_CHANCE
from ...data.ids import event_option_id, stable_seed
from ..ballistics import angle_blocked, bounce_direction, trace_path
from .. import throwing
from .. import weapons as weapons_pkg
from ...equipment.root_facts import root_action
from ..cast_fx import animate_ability, animate_consumable, animate_item_action
from ..constants import (
    ACTION_COUNT_LIMIT,
    PORTENT_DURATION_CAP,
    PROJECTILE_MAX_RANGE,
    ActionKind,
)
from .. import Material  # noqa: F401  (ink_doodle/blink 的 SOLID_AGGREGATE 判定)
from ..content import ITEM_DEFINITIONS, PROJECTILE_DEFINITIONS
from ..entities import ActionResult, Entity, Item, WorldItem

class MovementActionsMixin:
    """移动动作族：move_player/推墙/滑冰/开门/拔植物/等待。"""

    @root_action
    def move_player(self, dx: int, dy: int, *, choice: str | None = None) -> ActionResult:
        if max(abs(dx), abs(dy)) != 1:
            return ActionResult(False, tr("一次只能移动一格。"))
        from ...equipment import remaining_gear
        if not remaining_gear.before_move(self):
            return ActionResult(False, tr("换弹尚未完成，当前不能移位。"))
        if self.realm_id == "toy_memories" and self.realm_depth == 4 and dx and dy:
            return ActionResult(False, tr("推箱子区域只能沿四个方向移动。"))
        if getattr(self, "stasis_turns", 0) > 0:
            return ActionResult(False, tr("凝滞把你钉在了原地（剩余 {n} 回合）。", n=self.stasis_turns))
        if self.portents.get("sk_rooted", 0) > 0:
            # 未完停顿（核心执念主动技能）：1 回合内不能移动；攻击/道具/构想仍可用。
            return ActionResult(False, tr("句子被迫停顿——这一回合你挪不动步（剩余 {n} 回合）。", n=self.portents["sk_rooted"]))
        nx, ny = self.player.x + dx, self.player.y + dy
        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return ActionResult(False, tr("边界阻挡了你。"))
        target = self.entity_at(nx, ny)
        if choice is not None and (target is None or target is self.player or target.relation == '稳定意识'):
            return ActionResult(False, tr('本次动作选项已经失效'))
        if target and target is not self.player:
            if target.relation == "稳定意识" and target.integrity > 0:
                # 撞上稳定意识=唤起对话（与相邻交互键一致），绝不误伤交易对象。
                self.pending_npc_id = target.id
                self.talk_toy_keeper(target)
                return ActionResult(True, tr("{name}：「请讲。」", name=tr(target.label)), {"dialogue": target.id})
            # 近战规格（2026-09-22 修复）：手持武器定义 "melee" 时读它的
            # damage（伤害加成）/ segments（多段，逐段结算、击杀即停）/
            # time（基础耗时，<1 = 亚回合攻击）。旧实现一律 1 伤害 1 回合，
            # 手持武器的近战面完全不存在。
            action_plan = self.equipment.plan_action("melee", target=target, choice=choice)
            if not action_plan.valid:
                return self._fire_choice_result(action_plan, target=target)
            self._player_strike(
                target, "melee",
                segments=action_plan.segments,
                damage=1,
                attack_dir=(dx, dy),
                normal_melee=True,
                action_plan=action_plan,
            )
            self._spend_attack_time(action_plan.base_time, aptitude="melee")
            if target.integrity <= 0:
                self._resolve_enemy(target)
            self.messages.append(tr("你对 {target} 造成一次接触创伤。", target=tr(target.label)))
            return ActionResult(True, self.messages[-1], {"hit": target.id})
        # A preview/choice request is not a step and cannot advance inertia.
        if self.insight_active("夜行惯性"):
            self.night_walk_count = getattr(self, "night_walk_count", 0) + 1
            if self.night_walk_count >= 6:
                self.free_move_pending += 1
                self.night_walk_count = 0
                self.messages.append(tr("夜行的惯性带着你——这一步没有花时间。"))
        target_cell = self.cell(nx, ny)
        if "enlarged" in self.portents and target_cell.wall_kind in DOOR_KINDS:
            # 「放大」（2026-10-27 改）：1 格宽的缝隙不再阻挡移动，只是这一步
            # 的耗时翻倍（结算见下方 base_cost）；门仍然挤不过。
            # 逃逸阀只对门生效，避免被门永久锁死（见 _enlarged_door_escape）。
            if not self._enlarged_door_escape():
                return ActionResult(False, tr("放大的身体挤不过这扇门。"))
        if target_cell.solid:
            # 可推墙（石墨烯晶格）：撞上去把它推向同方向一格（推箱子，无法拉回）；
            # 下一格被墙/生物/边界挡住时推不动，回落为普通撞墙结算。
            pushed = self._try_push_wall(nx, ny, dx, dy)
            if pushed is not None:
                return pushed
            # 与墙（含空心积木墙、记忆容器、思绪容器等地面物体）相邻时，撞上去执行与
            # 左键点击该格完全相同的效果——徒手推倒可破坏的坚实聚合物，不可破坏的墙
            # 返回对应提示。键盘与鼠标行为就此统一，且不会引入左键做不到的键盘专属功能。
            return self.open_adjacent(nx, ny)
        origin = (self.player.x, self.player.y)
        identity_before = self._identity_before_move()
        self.facing = (dx, dy)
        self._last_player_move = (dx, dy)  # 回声抄写员镜像用
        self.player.x, self.player.y = nx, ny
        # 冰面：脚下是滑冰面就沿同方向一次性滑到头（撞墙/固体/生物/离开冰面
        # 为止），整个过程只花这 1 回合（时间结算在后面统一做）。
        contacts: list[tuple[int, int]] = [(nx, ny)]
        self._slide_on_ice(dx, dy, contacts)
        belt = floor_effect_for(self.cell(*origin)).conveyor
        if belt and (dx, dy) not in (belt, (-belt[0], -belt[1])):
            bx, by = self.player.x + belt[0], self.player.y + belt[1]
            if (0 <= bx < self.width and 0 <= by < self.height
                    and not self.cell(bx, by).solid and self.entity_at(bx, by) is None):
                self.player.x, self.player.y = bx, by
        nx, ny = self.player.x, self.player.y
        # 折好的逃生通道（2026-10-22 A2）：踏到通道的一端就被送到另一端。
        # 行动照旧只花这一次移动；不跨层、不跳任务门、边界与禁行格一律不送。
        from .. import item_devices
        jumped = item_devices.try_escape(self, (nx, ny))
        if jumped is not None:
            self.player.x, self.player.y = jumped
            nx, ny = jumped
        from ...equipment.expansion_runtime import note_player_move
        note_player_move(self, origin, (nx, ny))
        from ...equipment import gear_tools
        gear_tools.note_player_step(self, origin, (nx, ny))
        remaining_gear.after_move(self)
        # 地板足音（docs 261022 §6）：统一走真实落脚声径，空鼓地板只是 R=4 的一种。
        contacts.append((nx, ny))
        if self.insight_active('无声步') and self._quiet_step_charges_active():
            self.quiet_step_charges = max(0, self.quiet_step_charges - 1)
            if not self.quiet_step_charges:
                self.quiet_step_ready = False
        else:
            self.quiet_step_ready = False
        self._emit_step_noise(contacts, by_player=True)
        # 压力地板（逻辑触发源）：踏上/离开各发一次信号（强度 2）。
        self._pressure_step(origin, (nx, ny), by_player=True)
        # 踩踏植物：高丛被踩折成低草（无声、不提示）；稀有植物的踩踏反应
        # （缚魂藤缠脚、冥河柳渗水等）在这里一并结算——传玩家进去即代表
        # 「是玩家踩的」，异象走同一条通道（见 state.trample_plant）。
        self.trample_plant(nx, ny, self.player)
        self._reveal_disguises()
        self._mirror_attendants_step(origin, (nx, ny))
        # 玩家走进异象格（寻路滑步等边缘情形）时立即弹开堆叠的异象。
        self._separate_anomalies_at(nx, ny, exclude=self.player)
        self._apply_liquid_contact(nx, ny)
        self._identity_after_move(origin, identity_before)
        self._note_ebbing_departure()
        # 时间结算：免费步（松脱的缝线）与液面滑行（湿折页）不耗时；
        # 迟滞（纸浆 +0.5）与麻痹（静电尘 +0.2）等征兆按欠账折半补收，
        # 每积满 1.0 就多花 1 回合。洞察「液态亲和」免除纸浆的迟滞。
        # 传送带（扩展包 v1）：以起步格的传送带方向为基准——
        # 顺行：耗时减半（累积两次免一步）；逆行：耗时翻倍（+1 回合）；横跨：不变。
        belt_dir = floor_effect_for(self.cell(origin[0], origin[1])).conveyor
        belt_extra = 0.0
        if belt_dir:
            if (dx, dy) == belt_dir:
                self.belt_credit = getattr(self, "belt_credit", 0.0) + 0.5
                if self.belt_credit >= 1.0 - 1e-9:
                    self.belt_credit -= 1.0
                    self.free_move_pending += 1
            elif (dx, dy) == (-belt_dir[0], -belt_dir[1]):
                belt_extra = 1.0
        spent_free = False
        if self.free_move_pending > 0:
            self.free_move_pending -= 1
            spent_free = True
        elif self.free_liquid_moves > 0 and self.cell(nx, ny).liquid > 0:
            self.free_liquid_moves -= 1
            spent_free = True
        if spent_free:
            self.messages.append(tr("这一步没有花掉任何时间。"))
            # 免费步不推进世界，但玩家的占位改变了——门的状态要随之刷新
            # （踩上门打开、离开门关闭），否则免费步会留下错误的门状态。
            self._update_doors()
            self._tick_circuit_boards()
        else:
            extra = self._portent_move_penalty()
            extra += self._region_move_penalty()  # 悔恨之锚贴近：+0.5
            # 植物地形（2026-10-26）：磁带须/装订须/缝线丛 +0.5，千禧蒲草
            # 挺立时本格与 R1 +0.25；同类取最强，不叠成「一格走三回合」。
            extra += self.plant_move_penalty_at(nx, ny)
            # 2026-10-22：删除悬空的 weapon_weight 读取（全库无物品提供该效果，
            # 恒为 0；沉重的订书机描述早已改为只写伤害 +2，不再承诺移动惩罚）。
            extra += belt_extra  # 传送带逆行：耗时翻倍（+1 回合）
            # §12 H2 时缓区：玩家也同样变慢；多个时缓区只叠一次。
            try:
                from ..construct_environments import active as _active_fields
                if any(field['kind'] == 'slow_zone'
                       and (nx, ny) in {tuple(p) for p in field['cells']}
                       for field in _active_fields(self)):
                    extra += 0.3
            except Exception:
                pass
            if extra > 0:
                self.viscous_debt += extra
            base_cost = 1
            if (
                "honeyed" in self.portents
                and not self.memory_adapts("honey")
                and self._cell_holds_material(self.cell(nx, ny), "蜂蜜", 6)
            ):
                base_cost = 2  # 蜂蜜：上方生物移速减半（碎片「湿滑的经验」可免疫）
            # 「放大」（2026-10-27 玩家需求）：这一步只要涉及 1 格宽的狭窄地形
            # （起点格或终点格，含门——门格本身只可能经逃逸阀踏入），移动耗时
            # 翻倍。与蜂蜜的 2 相乘最高到 4，属于预期叠加。
            if "enlarged" in self.portents and (
                self._cell_too_narrow_for_enlarged(origin[0], origin[1])
                or self._cell_too_narrow_for_enlarged(nx, ny)
            ):
                base_cost *= 2
                self.messages.append(tr("放大的身体挤过缝隙，多花了些时间。"))
            if self.viscous_debt >= 1.0:
                self.viscous_debt -= 1.0
                self.messages.append(tr("粘稠的梦拖住了你的脚步。"))
                self._move_action_time(base_cost + 1)
            else:
                self._move_action_time(base_cost)
        return ActionResult(True, tr("你移动了一格。"), {"position": [nx, ny]})

    def _enlarged_door_escape(self) -> bool:
        """「放大」跨门的逃逸阀：站在门格上，或当前格的可通行邻格全是门。

        门的关闭状态是实心格，因此这里把「门」也算作可通行邻格——否则
        「四邻全是关着的门」永远凑不出来，玩家会被门永久锁死。只要满足其一，
        就允许跨门一次（门本身仍挤不过，例外只此一条）。
        """
        if self.cell(self.player.x, self.player.y).wall_kind in DOOR_KINDS:
            return True
        neighbours = [
            self.cell(self.player.x + dx, self.player.y + dy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= self.player.x + dx < self.width
            and 0 <= self.player.y + dy < self.height
        ]
        neighbours = [
            cell for cell in neighbours
            if not cell.solid or cell.wall_kind in DOOR_KINDS
        ]
        return bool(neighbours) and all(
            cell.wall_kind in DOOR_KINDS for cell in neighbours)

    def _move_action_time(self, amount: float) -> None:
        """本次主动步行已经处理传送带；世界结算不能再推回玩家。"""
        previous = getattr(self, '_conveyor_player_walking', False)
        self._conveyor_player_walking = True
        try:
            from ...equipment.remaining_gear import move_cost
            amount = move_cost(self, amount)
            self._action_time(amount)
        finally:
            self._conveyor_player_walking = previous

    def _apply_liquid_contact(self, x: int, y: int) -> None:
        """玩家进入材料格时的接触效果：液体显影 + 赋予液体与气体征兆。

        征兆的计时（冻结与衰减）在 _advance 里统一推进；这里只负责「踩进去
        就立刻沾染」。温热的恢复已改为只在持续期内按周期结算，接触瞬间不再
        直接回想象力。命名保留 _apply_liquid_contact 以免破坏既有调用点。
        """
        cell = self.cell(x, y)
        for portent_id in self._grant_material_portents(self.player, cell):
            self.messages.append(tr("你沾染了「{name}」的征兆。", name=tr(portent_def(portent_id).name)))
        # 水银：站位即触发（非征兆、不减速）——踩上水银液面时，本格气体的
        # 触发最小浓度被压低 5（至少 1），实际的降门槛在征兆判定里统一生效。
        if self._cell_holds_material(cell, "水银") and cell.gas > 0 and cell.gas_kind in GAS_DEFINITIONS:
            self.messages.append(tr("脚下的水银微微蒸腾：本格气体的触发浓度 −5（至少 1）。"))
        # 显影液不再在「站上去」的那一刻点亮一片半径 3 的暗格：它的显影范围
        # 完全由液流自己决定（见 _mark_developing_liquid），踩上去只是沾染征兆。

    def _reveal_disguises(self) -> None:
        """人形衣架：玩家进入其 2 格范围内时显形。"""
        for enemy in self.enemies:
            if enemy.integrity <= 0 or enemy.trait != "disguise":
                continue
            if enemy.alert_state == "未察觉" and max(abs(enemy.x - self.player.x), abs(enemy.y - self.player.y)) <= 2:
                enemy.alert_state = "怀疑"
                self.messages.append(tr("一件家具在你面前展开了轮廓——是人形衣架！"))

    def _mirror_attendants_step(self, origin: tuple[int, int], destination: tuple[int, int]) -> None:
        """镜像侍者：玩家移动时向相反方向移动一格（受阻则不动）。"""
        dx = destination[0] - origin[0]
        dy = destination[1] - origin[1]
        if dx == 0 and dy == 0:
            return
        for enemy in self.enemies:
            if enemy.integrity <= 0 or enemy.trait != "mirror_step":
                continue
            mx, my = enemy.x - dx, enemy.y - dy
            if not (0 <= mx < self.width and 0 <= my < self.height):
                continue
            if self.cell(mx, my).solid or self.entity_at(mx, my) is not None:
                continue
            enemy.x, enemy.y = mx, my

    def _try_push_wall(self, x: int, y: int, dx: int, dy: int) -> ActionResult | None:
        """可推墙（石墨烯晶格）的推箱子结算。

        把 (x,y) 的墙推向 (x+dx,y+dy)：目标格必须在界内、非坚实、没有生物
        （液体/气体/植物允许共存——晶格从它们上面碾过去）。推动花 1 回合；
        推不动返回 None，由调用方回落为普通撞墙。墙只能推、不能拉。
        """
        kind = self.cell(x, y).wall_kind
        if kind == '净衣推车':
            from ..hospital_scenes import push_hospital_cart
            pushed = push_hospital_cart(self, x, y, dx, dy)
            if pushed is not None:
                return pushed
        definition = wall_def(kind)
        if not definition.pushable:
            return None
        from ..expansion_consumables import block_push
        if block_push(self, x, y):
            self._action_time(1, ActionKind.MOVE)
            return ActionResult(True, tr('止退片挡住这次推动后碎裂了。'))
        if kind == "理念立方体" and dx and dy:
            return ActionResult(False, tr("立方体只能沿四个方向推动。"))
        tx, ty = x + dx, y + dy
        if not (0 <= tx < self.width and 0 <= ty < self.height):
            return self._push_wall_crush(x, y, definition)
        target = self.cell(tx, ty)
        if target.solid or self.entity_at(tx, ty) is not None:
            return self._push_wall_crush(x, y, definition)
        # 平移墙格：墙种、完整度、硬度/厚度/高度一并跟过去，原格还原为地面。
        target.wall_kind = kind
        target.solid = True
        target.integrity = self.cell(x, y).integrity
        target.hardness = self.cell(x, y).hardness
        target.thickness = self.cell(x, y).thickness
        target.height = self.cell(x, y).height
        source = self.cell(x, y)
        source.wall_kind = ""
        source.solid = False
        source.integrity = 100
        source.hardness = 2
        source.thickness = 1
        source.height = 0
        if kind == "理念立方体":
            origin = (self.player.x, self.player.y)
            identity_before = self._identity_before_move()
            self.player.x, self.player.y = x, y
            self._pressure_step(origin, (x, y), by_player=True)
            self._identity_after_move(origin, identity_before)
        self._material_index_ready = False
        # §10.5（2026-10-22 收口）：墙格位置改变＝厚度／高度布局变更，必须推进可听
        # 拓扑基准；否则挂起调查任务/寻路会把旧墙位置当成仍然有效。视野缓存同刻失效。
        self.topology_revision += 1
        from ..vision import cache as _vision_cache
        _vision_cache.invalidate(self)
        # docs 261022 §16.6：实际推移重物发 R=2（不叠加到玩家自身声径）。
        self._sound_pulse(tx, ty, 2, category="mechanical",
                          source=tr("推移重物"), announce=False)
        self._action_time(1, ActionKind.MOVE)
        self.messages.append(tr("立方体滑入下一格。" if kind == "理念立方体" else "晶格被你推着滑了一格。"))
        self._update_doors()
        return ActionResult(True, self.messages[-1], {"pushed_wall": [tx, ty]})

    def _push_wall_crush(self, x: int, y: int, definition) -> ActionResult | None:
        """把可推墙推向被挡死的方向：完整度 >150 时墙被挤碎（崩解度 +1）。

        只有玩家亲手推动会走到这里；普通推开不做伤害。完整度 <=150 的可推墙
        仍然只是「推不动」，不破坏。
        """
        cell = self.cell(x, y)
        if int(cell.integrity) <= 150:
            return None
        if not self.destroy_wall(x, y, "push"):
            return None
        self._action_time(1, ActionKind.MOVE)
        self.messages.append(tr("你把它推得嵌进阻碍里——{name}碎开了。",
                                name=tr(definition.name)))
        self._update_doors()
        return ActionResult(True, self.messages[-1], {"pushed_wall_destroyed": [x, y]})

    def _slide_on_ice(self, dx: int, dy: int, contacts: list | None = None) -> int:
        """冰面滑行：沿 (dx,dy) 一直滑，直到撞上墙/固体/生物或脚下不再是冰面。

        返回额外滑出的格数（0 = 脚下不是冰面，没滑）。不另耗回合，也不触发
        植物踩踏/液体接触——滑行是同一个动作的延续，落地后的那格交回给
        move_player 的常规落地结算。``contacts`` 记录真实接触到的每个落脚点，
        供统一足音按点发声（不是按动画帧）。
        """
        extra = 0
        while floor_effect_for(self.cell(self.player.x, self.player.y)).slide:
            tx, ty = self.player.x + dx, self.player.y + dy
            if not (0 <= tx < self.width and 0 <= ty < self.height):
                break
            target = self.cell(tx, ty)
            if target.solid or self.entity_at(tx, ty) is not None or not floor_effect_for(target).slide:
                break
            self.player.x, self.player.y = tx, ty
            extra += 1
            if contacts is not None:
                contacts.append((tx, ty))
            self._update_doors()
        return extra

    @root_action
    def open_adjacent(self, x: int, y: int) -> ActionResult:
        """处理相邻墙体的徒手操作：门直接打开并踏入；其它墙只有空心积木墙能徒手推倒。"""
        # 相邻取「8 邻域」（切比雪夫距离 1）：移动本就是 8 向的（move_player 不限制斜向），
        # 寻路也把门当成空气（path_to 的 passable 允许斜向穿门），所以斜向相邻的开门/推墙必须
        # 同样放行——否则斜向点门、以及寻路生成的「斜向过门」路径会在执行那一步被卡死。
        if max(abs(x - self.player.x), abs(y - self.player.y)) != 1:
            return ActionResult(False, tr("只能打开相邻的坚实聚合物。"))
        if not (0 <= x < self.width and 0 <= y < self.height) or not self.cell(x, y).solid:
            return ActionResult(False, tr("这里没有可以打开的坚实聚合物。"))
        cell = self.cell(x, y)
        if wall_def(cell.wall_kind).pushable:
            pushed = self._try_push_wall(x, y, x-self.player.x, y-self.player.y)
            if pushed is not None:
                return pushed
            return ActionResult(False, tr("目标位置被挡住，无法推动。"))
        component = self.circuit_node_at(x, y)
        if component and component[2]["op"] in {"toggle", "pulse"}:
            self._circuit_signal(x, y, by_player=True)
            self._action_time(1, ActionKind.USE)
            return ActionResult(True, tr("你操作了机关。"), {"circuit_input": component[1]})
        if cell.wall_kind in DOOR_KINDS:
            # 门仍然挤不过；只有 _enlarged_door_escape 的逃逸阀允许跨门。
            if "enlarged" in self.portents and not self._enlarged_door_escape():
                return ActionResult(False, tr("放大的身体挤不过这扇门。"))
            # 门：撞/点都打开并踏入（与「撞墙即左键」统一；门上有生物时已在 move_player
            # 走攻击分支）。门是「高墙」，关闭时相当于墙；此处在玩家占位之前先打「开」，
            # 随后 _update_doors 会因玩家站在门上而维持开启。
            self._open_door(cell)
            # docs 261022 §16.6：门状态确实改变才发 R=2 机械声。
            self._sound_pulse(x, y, 2, category="mechanical",
                              source=tr("门"), announce=False)
            origin = (self.player.x, self.player.y)
            identity_before = self._identity_before_move()
            self.player.x, self.player.y = x, y
            self._reveal_disguises()
            self._mirror_attendants_step(origin, (x, y))
            self._apply_liquid_contact(x, y)
            self._emit_step_noise([(x, y)], by_player=True)
            self._identity_after_move(origin, identity_before)
            self._action_time(1)
            self._update_doors()
            return ActionResult(True, tr("门开了，你跨了进去。"), {"position": [x, y]})
        definition = wall_def(cell.wall_kind)
        if not definition.hand_breakable:
            return ActionResult(False, tr("徒手无法破坏这种坚实聚合物。"))
        cell.integrity = max(0, cell.integrity - 7)
        if cell.integrity > 0:
            self._action_time(1)
            message = tr("{wall}松动了（完整度 {value}/{maximum}），再推几次就能推倒。", wall=tr(cell.wall_kind), value=cell.integrity, maximum=definition.integrity)
            self.messages.append(message)
            return ActionResult(True, message, {"integrity": cell.integrity})
        self._action_time(1)
        destroyed_kind = cell.wall_kind
        had_contents = cell.liquid > 0 or cell.gas > 0
        self.destroy_wall(x, y, "hand")
        message = tr("{wall}被你徒手推倒了。", wall=tr(destroyed_kind)) + (tr("封存的东西淌了一地。") if had_contents else "")
        if destroyed_kind == "黄粱米堆":
            # 生米入腹：恢复 3 点清醒度，随后坠入 2 回合深眠。
            self.restore_resource('lucidity', 3)
            self._apply_direct_portent(self.player, "deep_sleep", 2)
            message += tr("你捧起生米吃了下去，清醒度 +3，随后困意袭来。")
        self.messages.append(message)
        return ActionResult(True, message, {"opened": [x, y]})

    def _develop_terrain_radius(self, cx: int, cy: int, radius: int) -> int:
        """以 (cx, cy) 为中心 radius 半径内地形永久显影（含目标格）。"""
        developed = self.developed_for_depth()
        count = 0
        for y in range(max(0, cy - radius), min(self.height, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(self.width, cx + radius + 1)):
                if (x, y) not in developed and self.mark_developed(x, y):
                    count += 1
        return count

    @root_action
    def uproot_plant(self) -> ActionResult:
        """拔除脚下这格的植物（左键自己所在格 / Enter「行动」）：消耗一个行动。

        [SFX挂点] 建议拔起草叶的黏质音（素材库 环境氛围\ambient_squish_*）；
        core 纯逻辑，播放挂 UI 层（ACTION_SOUNDS 补映射即可）。
        """
        cell = self.cell(self.player.x, self.player.y)
        if not cell.plant:
            return ActionResult(False, tr("这里没有植物可拔。"))
        self._action_time(1, ActionKind.MISC)
        reward = self.uproot_plant_reward()
        self.set_plant_at(cell, 0)
        if reward:
            self.messages.append(reward)
            return ActionResult(True, reward)
        self.messages.append(tr("你把脚下的植物连根拔起了。"))
        return ActionResult(True, tr("你把脚下的植物连根拔起了。"))

    @root_action
    def wait(self) -> ActionResult:
        self._insight_wait_recovery()
        # 凝听：等待即进入（docs 261022 §16.3），覆盖当次等待及随后一个真实回合；
        # 先登记条件，再推进世界，敌人这一回合的足音才吃得到 −4 阈值。
        self.listen_until = max(self.listen_until, self.time + 2)
        # 扩展包洞察的读取规则由目录 kind 分发，不再往这里堆手写 if。观察算在
        # 推进世界之前，否则刚听到的两条线索会被这一回合的保留窗挤掉。
        from ..expansion_insights import on_wait as _expansion_insights_on_wait
        _expansion_insights_on_wait(self)
        self._action_time(1, ActionKind.MISC)
        # §11 §7：准备从这次真正推进世界的等待之后起算，查看面板不算。
        if self.insight_active('无声步'):
            self.quiet_step_charges = 2
            self.quiet_step_until = self.time + 4
            self.quiet_step_ready = True
        if self.insight_active('噪声耐受'):
            self.echo_ward_until = self.time + 4
        if self.insight_active('听声辨向'):
            self.sound_bearing_until = self.time + 4
        # §11 §7 静默惯习／局部照明：等待本身就是调查动作，不产生脉冲。
        if self.insight_active('静默惯习'):
            from ..vision.knowledge import record_iron_curtain_outline
            walls, entries = record_iron_curtain_outline(self)
            if walls:
                self.messages.append(tr(
                    '你贴着沉思铁幕等待，借振动记下 {walls} 个墙格的 {entries} 处开放入口。',
                    walls=walls, entries=entries))
        if self.insight_active('局部照明'):
            from ..vision.knowledge import record_light_snapshot
            lit = 0
            for nx, ny in ((self.player.x + 1, self.player.y),
                           (self.player.x - 1, self.player.y),
                           (self.player.x, self.player.y + 1),
                           (self.player.x, self.player.y - 1)):
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                cell = self.cell(nx, ny)
                if cell.light_radius > 0 and cell.light_on and self.is_visible(nx, ny):
                    lit += record_light_snapshot(self, nx, ny)
            if lit:
                self.messages.append(tr('你借着身旁的光，记下 {n} 格地形。', n=lit))
        if self.insight_active("守株待兔"):
            self.ambush_ready = True
            self.messages.append(tr("你守在原地不动——下一次攻击蓄足了劲（创伤 +2）。"))
        return ActionResult(True, tr("你等待了一个行动。"))

    def _insight_wait_recovery(self) -> None:
        cell = self.cell(self.player.x, self.player.y)
        contacts = set(self._material_portent_ids(cell))
        rules = {
            '抗灼': ('scalded',), '冷韧': ('frozen',),
            '抗辐射体质': ('irradiated',),
            '磁头清洁': ('rewind_lag',), '绝缘体质': ('shocked',),
            '不燃体质': ('burning',), '稳立不摇': ('sk_rooted',),
            '梦魇老主顾': ('nightmare', 'nightmare_fiber', 'nightmare_breath'),
        }
        for insight, portents in rules.items():
            if not self.insight_active(insight):
                continue
            for pid in portents:
                if pid not in self.portents:
                    continue
                if insight in ('抗辐射体质', '梦魇老主顾') and pid in contacts:
                    continue
                self._remember_portent_end(self.player, pid)
                self.messages.append(tr('你利用「{name}」调整自己，解除了「{portent}」。',
                                        name=tr(insight), portent=tr(portent_def(pid).name)))
        if self.insight_active('液态亲和') and cell.liquid > 0:
            from ...materials import material_cleanses
            cleansable = material_cleanses('水')
            pid = next((pid for pid in self.portents if pid in cleansable), None)
            if pid:
                self._remember_portent_end(self.player, pid)
    def _push_entity(self, target: Entity, dx: int, dy: int, force: int) -> None:
        if target is self.player and self.cell(target.x,target.y).liquid>0:
            from ...equipment.remaining_gear import equipped
            if equipped(self,'expansion.terrain.e05'):
                force=max(0,force-1)
        if target.relation == '玩偶意识体':
            return  # Fixed tutorial targets also stay put when struck by knockback.
        if target.trait == "relentless":
            # 原初不息：不可被推动——撞击方向的动量转为 1 点完整度损伤。
            self._kill_full_reward = True
            target.integrity = max(0, target.integrity - 1)
            return
        for _ in range(min(3, force)):
            nx, ny = target.x + dx, target.y + dy
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                self._kill_full_reward = True  # 玩家弹体：崩解全额
                target.integrity = max(0, target.integrity - 1)
                return
            if self.cell(nx, ny).solid:
                self._kill_full_reward = True  # 玩家弹体：崩解全额
                target.integrity = max(0, target.integrity - 1)
                return
            if self.entity_at(nx, ny) is not None:
                self._kill_full_reward = True  # 玩家弹体：崩解全额
                target.integrity = max(0, target.integrity - 1)
                return
            target.x, target.y = nx, ny
