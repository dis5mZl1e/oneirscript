"""视野：视野预算模型（黑烟截断、灰尘云衰减）与布雷森汉姆视线。

这是视野子系统（``core/vision/``）的核心，由 GameState 继承（见 core/state.py）：

- :mod:`dream_demo.core.vision.glow`：发光地衣把没有遮挡的方向上的视距延长一段；
- :mod:`dream_demo.core.vision.cache`：可见集合按「依赖签名」缓存，避免 30fps 重算。

寻路已迁往独立子系统 core/pathing/（``PathMixin.path_to`` 供玩家与异象共用）。
"""

from __future__ import annotations

from ...materials import (
    DOOR_KINDS,
    GAS_DEFINITIONS,
    TRANSPARENT_WALLS,
    floor_effect_for,
    plant_height,
    wall_def,
)
from ..constants import SIGHT_OBSCURE_MIN
from ..entities import Cell
from . import cache, glow
from ...data.anomalies import ANOMALY_DEFINITIONS  # noqa: E402
# CY-3 开关的模块级绑定（与 persistence / materials_sim / app 同一种写法）：
# 仍然每次调用现读活环境，只是省掉函数内 `from ... import enabled` 的重复 import。
from ...cy_kernels import enabled as _kernel_enabled  # noqa: E402


class SightMixin:
    def effective_sight_radius(self) -> int:
        """实际视野半径：灯塔透镜在下潜后的前 3 回合 +3；遮蔽等征兆按 vision 修正。

        （照彻是「全图照亮」，不走半径，另见 is_visible。）

        🔴 回合内缓存（2026-10-10 性能 P0）：视野计算对 ~R² 个可见格逐格调
        本方法，而链条末端 `_portent_vision_delta → _effect_power →
        equipment.compiled()` 是全量重编译——实测每走一步要编译上千次装备
        （详见 docs/perf-move-diagnosis-and-board-ux-plan.md §1）。半径的全部
        输入都是回合/位置粒度（征兆、装备、望远层数、贴墙、脚下地板），因此
        键 = (回合, 玩家坐标, 望远层数, 征兆集合, 夜视洞察, 脚下地板变体)。
        征兆/洞察/地板进键是为了「绕过 apply 的直改」（调试与测试直改 state
        后立即断言视野）也不穿帮；装备/记忆/下潜回合计入 `GameSession.apply`
        开头的统一失效（玩家路径上它们只在动作里变化）。
        """
        px, py = self.player.x, self.player.y
        key = (self.time, px, py,
               self.ability_turns.get("farsight", 0),
               tuple(sorted(self.portents)),
               int(getattr(self.player, "blind_turns", 0.0) > 0),
               self.insight_active("夜视"),
               self.insight_active("边界脚本"),
               self.depth,
               self.cell(px, py).aggregate_variant if (0 <= px < self.width and 0 <= py < self.height) else "")
        cached = getattr(self, "_sight_radius_cache", None)
        if cached is not None and cached[0] == key:
            return cached[1]
        profile = self._vision_profile()
        # ---- 正面阶段：所有 +视距来源走同一通道（docs 261022 §14.1 末行）----
        radius = self.sight_radius + profile.positive
        if self.insight_active("夜视"):
            radius += 1
        # 边界脚本（扩展包 v2）：深层边界（28–30）视野 +1。depth 进缓存键——
        # 下潜改 depth 时不靠 apply 统一失效也不穿帮。
        if self.insight_active("边界脚本") and self.depth >= 28:
            radius += 1
        equipped_ids = {item.definition_id for item in self.equipped_items()}
        if "lighthouse_lens" in equipped_ids and self.turns_since_descend <= 3:
            radius += 3
        radius += self._effect_power("vision_up")  # 夜灯的电池：视野 +1
        radius += self.memory_stat_bonus("sight")  # 记忆碎片「移动的视窗」：视野 +1
        radius += self._floor_sight_bonus()  # 站在反光聚合物上：视野 +1
        # 「月下」（流动月光 / 夜皇后）现在走目录的 vision=4，与风向感应、晨视同
        # 一个正面通道；旧实现把它写死在这里，异象侧完全读不到（docs §14.1 末行）。
        radius += 4 if self.ability_turns.get("farsight", 0) > 0 else 0
        # ---- 平减阶段：同族取最大后相加，无光绒墙贴近与失焦各自成族 ----
        from ...equipment import gear_light
        # 光类装备（2026-10-25 批次二）：磨砂护目片的「暗处辨认距离缩短」走同一条
        # 平减通道；没带光类装备时这一句只是一次行囊扫描，不会编译装备。
        radius += profile.flat + self._region_sight_penalty() + gear_light.vision_flat(self)
        if profile.blur:
            # 失焦（错贴标签）：只对本项设「最多减到 3」。别的强限视不会因为失焦
            # 被解除，失焦也不会把已经很低的视野重新抬起来。
            radius = max(radius + profile.blur, min(profile.blur_floor, radius))
        # ---- 比例阶段：跨族取最小倍率；旧 blind_turns 的半视野同走这一道 ----
        ratio = profile.ratio
        if getattr(self.player, "blind_turns", 0.0) > 0:
            ratio = min(ratio, 0.5)
        radius = max(0, radius)
        if ratio < 1.0:
            radius = int(radius * ratio)
        # ---- 致盲覆盖：普通视觉归零；光源延伸与照彻都不能把它复活 ----
        # 磨砂护目片把「强光致盲」缓冲成一半而不是清零（批次二），未佩戴时仍是 0。
        if profile.blinds:
            radius = gear_light.blind_radius(self, radius)
        self._sight_radius_cache = (key, radius)
        return radius

    def _vision_scale(self, observer) -> float:
        """该观察者当前的比例缩视倍率，用来同比例削减「光源延伸」。

        docs 261022 §14.1：强光延伸须同受比例缩视，站进灯里不能完整抵消全部
        减视野效果；`blinds` 直接给 0——普通视觉归零后，光源延伸也不能复活它。
        """
        profile = (self._vision_profile() if observer is self.player
                   else self._vision_profile(observer))
        if profile.blinds:
            return 0.0
        ratio = profile.ratio
        if getattr(observer, "blind_turns", 0.0) > 0:
            ratio = min(ratio, 0.5)
        return max(0.0, float(ratio))

    def _floor_sight_bonus(self) -> int:
        """脚下地板的视距加成（反光聚合物：映出光线，视野 +1）。

        只算**玩家所在格**的地板：站在镜面般的聚合地面上时，四周的光多
        反射一点回来。地板效果一律通过 materials/floor_def 的旗标查询——
        非聚合地面（液态记忆等）即便残留变体名也不生效。
        """
        if not (0 <= self.player.x < self.width and 0 <= self.player.y < self.height):
            return 0
        return floor_effect_for(self.cell(self.player.x, self.player.y)).sight_bonus

    @staticmethod
    def _gas_sight_effect(cell: Cell) -> tuple[bool, float]:
        """类墙体气体效果：返回（是否完全阻断视线, 透过后的剩余视野倍率）。

        黑烟如墙般挡死这一条视线；灰尘云把「透过它之后」还能看到的距离按
        倍率收缩——不影响其他方向的射线，也不影响透过之前已经走过的那段视野。

        起效判定按 **遮蔽强度**（浓度 × 该气体的 opacity）而不是固定浓度 20：
        黑烟/灰尘在扩散中会被摊薄（实测 80 浓度的单团十来回合就降到 20 以下），
        若只认「浓度 ≥ 20」，遮蔽效果几乎只在刚生成的那几回合、且仅限源头那一格
        生效——这正是「代码写了却看不出效果」的原因。改用强度后，薄而广的烟云
        同样能遮蔽，与观感一致。
        """
        definition = GAS_DEFINITIONS.get(cell.gas_kind)
        if definition is None:
            return False, 1.0
        # 遮蔽强度 = 浓度 × opacity 权重；opacity 越高，越薄的浓度就能遮挡。
        strength = cell.gas * (definition.opacity / 100.0)
        if strength < SIGHT_OBSCURE_MIN:
            return False, 1.0
        if definition.blocks_sight:
            return True, 0.0
        if definition.sight_attenuation < 1.0:
            return False, definition.sight_attenuation
        return False, 1.0

    def _sight_obstruction(self, cell: Cell) -> tuple[bool, int]:
        """这一格对视线的遮挡效果：返回 (是否完全挡死, 额外削减的剩余视距)。

        玩家口径（2026-10-24 裁定）：**高度决定遮挡**。

        - 透明墙（TRANSPARENT_WALLS，如玻璃幕墙）始终完全透光，不论高度；
        - 门（DOOR_KINDS）保持原有的显式例外：无论开合都挡死视线。开着的门
          solid=False、height=0，所以必须按墙种先判，不能被高度漏过；
        - 2 格高的植物（高丛）保持原有的挡死；
        - 高度 >= 3：完全挡死（压实聚合墙／意识边界这类「高墙」）；
        - 高度 == 2：不挡死，但吃掉墙后最多 3 格的剩余视距；
        - 高度 <= 1：完全不挡（木桌子、石台、陷阱石台／机关石台、记忆容器／
          思绪容器、潮解纸墙、枕木、云块……玩家可以看过去）。

        高度优先读 cell.height；历史存档／直改格子里 height == 0 的实心墙退回
        到墙种目录的 height（_open_door 会把开着的门压成 0，但它在上面的门种
        分支已先行判掉；可步行特征墙的 height 由 configure_wall 写入，不依赖
        这条兜底）。

        性能：每格一次整数比较 + 最多一次 WALL_DEFINITIONS 字典查询，不分配
        容器，供 _sight_reaches / _has_line_of_sight 的逐格热循环共用。
        """
        kind = cell.wall_kind
        if kind:
            # 透明墙先判：玻璃幕墙这类高度 3 的透明墙仍要完全透光。
            if kind in TRANSPARENT_WALLS:
                return False, 0
            if kind in DOOR_KINDS:
                return True, 0
        if cell.plant and plant_height(cell.plant) >= 2:
            return True, 0
        # 高度是**固体**的属性：被清掉/可穿行的格子（solid=False）即使残留
        # height（旧场景改写、直改测试夹具），也不该凭空挡住视线。
        if not cell.solid:
            return False, 0
        if not kind:
            # 没有墙种的实心格无法按材料/高度分类（多见于地图边界与手改夹具），
            # 保持旧口径：保守地当作挡死，不让「不明实心格」变成隐形通道。
            return True, 0
        height = cell.height
        if height <= 0:
            # 兜底：旧档／直改格子没写 height 的实心墙按目录高度算。
            height = int(getattr(wall_def(kind), "height", 0) or 0)
        if height >= 3:
            return True, 0
        if height == 2:
            return False, 3
        return False, 0

    def _sight_reaches(self, x1: int, y1: int, bonus: int = 0, *,
                       use_kernel: bool | None = None) -> bool:
        return self._observer_sight_reaches(self.player, x1, y1,
                                           self.effective_sight_radius()+bonus,
                                           use_kernel=use_kernel)

    def can_see(self, observer, x: int, y: int) -> bool:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        radius = self.effective_sight_radius() if observer is self.player else self._effective_vision(observer)
        if radius <= 0:
            # 归零之后只剩自身格：灯光延伸与照彻都不能复活普通视觉（§14.1）。
            return (x, y) == (observer.x, observer.y)
        dx, dy = abs(observer.x-x), abs(observer.y-y)
        # Retain each mover's established sight-distance metric.
        distance = max(dx, dy) if observer is self.player else dx+dy
        # 机械照明只延长「无遮挡方向」的视距：+3，专门强光最多 +4，多光源取
        # 最高不求和；V=0 已在上面直接返回，灯光不能复活视觉（docs 261022 §4.1）。
        bonus = glow.sight_bonus(self, x, y) if distance > radius else 0
        if bonus:
            # §14.1：强光延伸同受比例缩视，站进灯里不能完整抵消全部减视野效果。
            bonus = int(bonus * self._vision_scale(observer))
        shadow = 0
        from ...equipment import gear_light
        if observer is self.player:
            # 光类装备的逐格修正（正面锥 +1／背后 −1／遮光面切格）：遮住即不可见，
            # 与 ``visible_cells`` 及逐格实时可见判定共用同一张表，不会两套口径打架。
            shift = gear_light.cell_shift(self, x, y)
            if shift is None:
                return False
            bonus += shift
            bonus = max(bonus, gear_light.extra_span(self, x, y, radius))
        elif (x, y) == (self.player.x, self.player.y):
            # 异象看你时：漏光的刀（更显眼）与黑布背心／遮片（更不显眼）只改这一次
            # 半径比较，不改它看别的东西的视距。
            radius += gear_light.seen_delta(self, observer)
            # 洞察「光圈的边缘」：停在明暗交界留的那一手，只在暗处少露一格光。
            from ..expansion_insights import dim_edge_shadow, dim_edge_spend
            shadow = dim_edge_shadow(self)
            radius += shadow
        if distance > radius+bonus:
            if shadow and distance == radius + bonus - shadow:
                # 差这一格：正是「光圈的边缘」把它挡下的，用掉即失效
                # （所谓「减少**一次**视觉暴露」）。
                dim_edge_spend(self)
            return False
        return self._observer_sight_reaches(observer, x, y, radius+bonus)

    def set_light_enabled(self, x: int, y: int, enabled: bool) -> bool:
        cell = self.cell(x, y)
        from ..realm_lights import cancel_borrowed_light
        cancelled = cancel_borrowed_light(self,(x,y))
        if cell.light_on == enabled and not cancelled:
            return False
        cell.light_on = enabled
        for record in self.world_ledger.facilities.values():
            if (record.layer_key==self.layer_key() and record.definition_id.startswith('encounter.')
                    and record.cell('lamp')==(x,y)):
                fields=dict(self.world_ledger.terrain_for(self.layer_key()).get(f'{x},{y}',{}))
                fields['light_on']=enabled
                self.world_ledger.mark_terrain(self.layer_key(),x,y,**fields)
        cache.invalidate(self)
        return True

    def toggle_light(self,x: int,y: int):
        from ..action_permissions import stasis_refusal
        refused=stasis_refusal(self)
        if refused is not None: return refused
        from ..entities import ActionResult
        from ..constants import ActionKind
        from ...i18n import tr
        if not (0<=x<self.width and 0<=y<self.height):
            return ActionResult(False,'')
        if max(abs(x-self.player.x),abs(y-self.player.y))>1 or not self.is_visible(x,y):
            return ActionResult(False,'')
        cell=self.cell(x,y)
        if cell.light_radius<=0:
            return ActionResult(False,tr('这里没有可以切换的光源。'))
        # §12 F：两种设施不接受手动开关——余烬灯盏靠火，弧光灯架靠电路。
        # 不给它们开关，才谈得上「断电即灭」「点火/灭火才是操作」。
        from ...materials import FLAME_FIXTURE_KINDS, POWERED_FIXTURE_KINDS
        if cell.wall_kind in FLAME_FIXTURE_KINDS:
            return ActionResult(False,tr('这盏灯靠燃烧发光——点火或灭火，而不是拨开关。'))
        if cell.wall_kind in POWERED_FIXTURE_KINDS:
            return ActionResult(False,tr('灯架的电源接在电路上，这里没有可以拨的开关。'))
        enabled=not cell.light_on
        self.set_light_enabled(x,y,enabled)
        self._action_time(1,ActionKind.USE)
        message=tr('光源已点亮。' if enabled else '光源已熄灭。')
        self.messages.append(message)
        return ActionResult(True,message)

    def _observer_sight_reaches(self, observer, x1: int, y1: int, radius: int,
                                use_kernel: bool | None = None) -> bool:
        """沿布雷森汉姆视线逐格推进，把视野当作一条会耗尽的预算。

        每推进一格耗 1 点预算；黑烟立刻截断；灰尘云把「尚未走完的剩余预算」
        按倍率收缩（已走过的部分不受影响，其他方向的射线也不受影响）。预算
        用浮点，因此衰减之后仍能走完最后一格的部分距离。

        遮挡按高度结算（见 :meth:`_sight_obstruction`）：高度 ≥3、门、高丛
        直接截断；高度 2 的固体只从「墙后」的剩余预算里扣 3 格（墙格本身与它
        之前的格子照常可见）；高度 ≤1 与透明墙完全不挡。

        ``bonus`` 给这次射线额外增加一点预算（发光地衣的照亮延长，见
        core/vision/glow.py）。它只让射线**走得远一点**，不能让它穿过墙、
        门、黑烟或高丛——遮挡判定与步数累加都在同一条循环里，因此「延长
        视距但不穿透遮挡」是免费的。

        性能（2026-10-27 A5）：CY-3 开关由**一个可见集计算**的开头解析一次
        （``visible_cells`` / ``live_sight``）再经 ``use_kernel`` 传进来。旧写法
        是每调用一次本函数就 ``enabled("sight")`` 一次：一次 ``wait`` 动作的
        ``visible_cells`` 重算会对约 630 个候选格各调一次，纯重复付费约
        1.3ms/动作。``use_kernel=None`` 表示「没有批内值」（``can_see``／
        ``glow.reveals`` 等单格入口），此时仍在这里现读，因此开关不跨调用缓存。
        """
        if use_kernel is None:
            # 单格入口没有批内开关可复用：现读，保证运行时切换
            # ONEIRSCRIPT_CY_KERNEL_SIGHT 在下一次调用立即生效。
            use_kernel = _kernel_enabled("sight")
        if use_kernel:
            # CY-3：编译内核只接管射线循环；规则判定仍在 state 方法上。
            from .sight_kernel import observer_sight_reaches
            return observer_sight_reaches(self, observer, x1, y1, radius)
        x0, y0 = observer.x, observer.y
        if (x0, y0) == (x1, y1):
            # 自己脚下这一格始终可读：致盲把普通视觉归零后，玩家自身与所在格
            # 仍然显示（docs 261022 §14.1）。
            return True
        budget = float(radius)
        if budget <= 0:
            return False
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        error = dx - dy
        x, y = x0, y0
        step = 0
        skill_blocked = self._skill_sight_blockers() if hasattr(self, "_skill_sight_blockers") else set()
        from ..construct_environments import light_curtain_cells
        skill_blocked = skill_blocked | light_curtain_cells(self)
        while (x, y) != (x1, y1):
            doubled = 2 * error
            if doubled > -dy:
                error -= dy
                x += sx
            if doubled < dx:
                error += dx
                y += sy
            step += 1
            if step > budget:
                return False
            if (x, y) == (x1, y1):
                break  # 目标格本身总是可见（可见的墙、可见的烟团）
            cell = self.cell(x, y)
            if (x, y) in skill_blocked:
                return False
            # 高度决定遮挡（2026-10-24 玩家口径）：1 格高的固体让视线完全通过；
            # 2 格高只吃掉墙后最多 3 格的剩余预算；3 格及以上挡死。门与高丛、
            # 透明墙的例外在 _sight_obstruction 里统一。
            blocks, penalty = self._sight_obstruction(cell)
            if blocks:
                return False
            if penalty:
                # 只削减「墙后」的剩余预算：走到墙格本身花掉的 step 不受影响，
                # 因此墙格自身与它之前的格子照常可见。
                budget = max(float(step), budget - penalty)
            blocked, attenuation = self._gas_sight_effect(cell)
            if blocked:
                return False
            if attenuation < 1.0:
                budget = step + (budget - step) * attenuation
        return True

    def live_sight(self, x: int, y: int) -> bool:
        """这一格是否在**普通观察**之下（视线、照彻、调试全视、发光地衣延长）。

        与 :meth:`is_visible` 的差别：这里不包含「存在性感知」——核心执念常驻、
        诅咒灵视揭示失控意识那两条走 :meth:`perceived_creatures`。格子详情面板
        要按对象分别判定权限（§16），只有感知到某个生物时才允许列出该生物，
        不能因为「这一格有个恒显执念」就把同格的地形、液体和其他生物一并摊开。
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        if self.light_turns > 0:
            # 空心的灯塔「照彻」：照亮期内本层全图可见（实体也暴露）。
            # 2026-10-22 裁定「全图真照亮」后，这里与 `visible_cells` 的照彻
            # 分支口径一致（那条也从逐格射线改成了全区）。
            # 照彻仍是「普通视觉」的光源延伸：致盲把 V 归零之后它照不回来
            # （docs 261022 §14.1）。
            return self.effective_sight_radius() > 0
        if getattr(self, "debug_full_vision", False):
            return True
        from ...equipment import gear_light
        # 光类装备（2026-10-25 批次二）的逐格修正：正面锥 +1、背后 −1、遮光面/
        # 遮片把整格切掉。没有光类装备时 ``cell_shift`` 直接返回 0。
        shift = gear_light.cell_shift(self, x, y)
        if shift is None:
            return False
        # 本函数按格调用（is_visible／面板／边框），一次判定最多走两条射线；
        # 开关在这里解析一次再传下去（2026-10-27 A5）。同一调用内的可见性不依赖
        # 开关中途变化，逐射线现读等于为同一次判定付两遍 enabled()。
        use_kernel = _kernel_enabled("sight")
        if self._sight_reaches(x, y, shift, use_kernel=use_kernel):
            return True
        span = gear_light.extra_span(self, x, y, self.effective_sight_radius())
        if span and self._sight_reaches(x, y, span, use_kernel=use_kernel):
            return True
        return glow.reveals(self, x, y)

    def perceived_creatures(self, x: int, y: int) -> list:
        """这一格里**仅凭存在性感知**（而非视线）就能知道的生物。

        两条来源都来自旧 ``is_visible`` 里的循环，口径完全不变：

        - 核心执念恒显（2026-09-22）：无论距离、隔挡与清醒度，你总能「感觉到」
          核心执念在哪——这是剧情实体的存在性感知，不是照明；
        - 诅咒灵视（2026-09-22 改版）：征兆持续期间，所有失控意识（含伪装）
          的所在格同样视为在视野中。

        返回的是**这一格的全部**此类生物，旧实现只把它当作一个布尔用，
        因此同一格叠了两个失控意识时「可见」这件事没有区别，但现在格子详情
        要把每一只都列出来，必须逐个收集而不是命中第一就返回。
        """
        found = []
        for enemy in self.enemies:
            if enemy.integrity <= 0 or enemy.x != x or enemy.y != y:
                continue
            if enemy.relation != "失控意识":
                continue
            definition = ANOMALY_DEFINITIONS.get(getattr(enemy, "catalog_id", ""), {})
            if definition.get("anomaly_kind") == "核心执念" or self.reveals_anomalies:
                found.append(enemy)
        return found

    def is_visible(self, x: int, y: int) -> bool:
        """Return whether a cell is in the player's current, wall-blocked sight.

        除了纯视线，被发光地衣照亮的格子也算：光照把视距延长几格，但延长
        走的仍是同一条会被遮挡截断的射线（core/vision/glow.py），因此它
        只是「看得更远一点」，不会让墙后的东西显形。

        视野之外还包含存在性感知（:meth:`perceived_creatures`）：那一格的地形与
        实体照常渲染，等于白板征兆（旧实现只画轮廓、is_visible 仍为 False，
        导致悬停/观测/攻击等一切「需要看见」的交互全部无效）。
        """
        return self.live_sight(x, y) or bool(self.perceived_creatures(x, y))

    def visible_cells(self) -> set[tuple[int, int]]:
        """当前可见的格子集合（带缓存，见 core/vision/cache.py）。"""
        key = cache.signature(self)
        cached = cache.load(self, key)
        if cached is not None:
            return cached
        radius = self.effective_sight_radius()
        if radius <= 0:
            # 致盲（docs 261022 §14.1）：普通视觉归零后，光源延伸与照彻都不能把它复活，
            # 可见集合只剩脚下这一格（地图记忆与背包／面板照常）。
            return cache.store(self, key, {(self.player.x, self.player.y)})
        # CY-3 开关：**本次重算**开头解析一次（2026-10-27 A5）。下面每格最多调
        # 3 次 _sight_reaches，旧写法逐格 enabled("sight")——实测 ≈630 次/动作
        # ≈1.3ms。粒度只到「一次可见集计算」：不跨调用、不跨动作缓存，下一次
        # 重算再读，运行时切换 ONEIRSCRIPT_CY_KERNEL_SIGHT 依旧下一拍立即生效。
        use_kernel = _kernel_enabled("sight")
        # §11 P0：一次视野解析内复用光源半径；退出后恢复原状态，避免跨动作
        # 使用过期光照。没有缓存的 is_visible 调用仍按单次 source_radius 判定。
        previous_glow_cache = getattr(self, "_glow_radius_cache", None)
        previous_sources = getattr(self, "_glow_sources_cache", None)
        self._glow_radius_cache = {}
        try:
            player_x, player_y = self.player.x, self.player.y
            sources = glow.sources_in_window(
                self, (player_x, player_y),
                radius + glow.MAX_SIGHT_BONUS + glow.MAX_SOURCE_RADIUS)
            self._glow_sources_cache = sources
            if self.light_turns > 0:
                # 空心灯塔「照彻」＝**全图真照亮**（2026-10-22 裁定，A5 剩余项）。
                # 这里原先只收 `_has_line_of_sight` 的格子，于是同一回合里
                # 渲染（本函数）看不见墙后、交互（`live_sight` 直接返回 True）
                # 却能点墙后——两套口径打架。裁定按设计文案统一到「全图」：
                # 数值总表「全图被照亮：你看得见所有异象」、
                # 内容扩展方案「2 回合内玩家视野覆盖全图」。
                # 顺带也更快：比原来的逐格射线便宜。
                cells = {(x, y) for y in range(self.height) for x in range(self.width)}
            else:
                # 机械照明能把视距延长 MAX_SIGHT_BONUS 格（强光 +4，不会更远），
                # 因此窗口比视距半径大一圈；没有光源时按原半径走，不做无谓的重算。
                reach = radius + glow.MAX_SIGHT_BONUS if sources else radius
                # C1（docs 261022 §4.1）：先把「哪些格被机械光延长、延长几格」一次
                # 算成表，再逐格判定。旧写法每个候选格都调一次 glow.reveals →
                # glow.sight_bonus（对每格重扫一遍光源列表）；这里只是把遍历方向
                # 反过来，规则与 glow.sight_bonus 逐项一致：多来源取最高、遮挡仍
                # 走同一条 _has_line_of_sight 射线、V=0 已在上面提前返回。
                bonus_by_cell = glow.sight_bonus_map(self, sources) if sources else {}
                # 光类装备（批次二）：一张「正面锥／背后／遮光面」表，一次解析只算
                # 一遍；没有光类装备时 overlay 为 None，下面两处判断都直接跳过。
                from ...equipment import gear_light
                table = gear_light.overlay(self)
                extra = set(table["extra"]) if table else set()
                if extra:
                    # 被引到远处的光可能落在视距圈外，扫描窗口按它再放一圈。
                    reach = max(reach, max(max(abs(ex - player_x), abs(ey - player_y))
                                           for ex, ey in extra))
                cells = set()
                for y in range(max(0, player_y - reach), min(self.height, player_y + reach + 1)):
                    for x in range(max(0, player_x - reach), min(self.width, player_x + reach + 1)):
                        shift = 0
                        if table is not None:
                            shift = gear_light.shift_of(table, x, y)
                            if shift is None:
                                continue
                        if self._sight_reaches(x, y, shift, use_kernel=use_kernel):
                            cells.add((x, y))
                            continue
                        bonus = bonus_by_cell.get((x, y), 0)
                        if shift > 0:
                            bonus = max(bonus, shift)
                        if bonus and self._sight_reaches(x, y, bonus,
                                                         use_kernel=use_kernel):
                            cells.add((x, y))
                            continue
                        if (x, y) in extra:
                            # 被引过去／闪出来的光：那几格算「亮着」，看得见多远处
                            # 都按同一条带预算的射线结算（墙后照样不行）。
                            span = gear_light.extra_span(self, x, y, radius)
                            if span and self._sight_reaches(x, y, span,
                                                            use_kernel=use_kernel):
                                cells.add((x, y))
                # 本帧的延长表顺手发布给逐格问句（glow.sight_bonus），免得同一
                # 步里 can_see／reveals 再逐格重扫 49 格光源窗口。
                glow.publish_frame(self, key, radius + glow.MAX_SIGHT_BONUS,
                                   bonus_by_cell)
        finally:
            if previous_glow_cache is None:
                try:
                    del self._glow_radius_cache
                except AttributeError:
                    pass
            else:
                self._glow_radius_cache = previous_glow_cache
            if previous_sources is None:
                try:
                    del self._glow_sources_cache
                except AttributeError:
                    pass
            else:
                self._glow_sources_cache = previous_sources
        return cache.store(self, key, cells)

    def proximity_effects(self) -> list[str]:
        effects: list[str] = []
        # 单边耳机的降噪代价：悬停"贴近"提示不再显示。
        if self.equipment.has_effect("noise_cut"):
            return effects
        for x, y in (
            (self.player.x + 1, self.player.y),
            (self.player.x - 1, self.player.y),
            (self.player.x, self.player.y + 1),
            (self.player.x, self.player.y - 1),
        ):
            if not (0 <= x < self.width and 0 <= y < self.height):
                continue
            cell = self.cell(x, y)
            if not cell.solid:
                continue
            effect = wall_def(cell.wall_kind).proximity_effect
            if effect and effect not in effects:
                effects.append(effect)
        return effects

    def _has_line_of_sight(self, x0: int, y0: int, x1: int, y1: int) -> bool:
        """Integer Bresenham visibility; blocking follows cell height.

        与玩家视野预算共用 :meth:`_sight_obstruction` 的高度口径，但这是布尔
        接口、没有半径：高度 2 的固体**通过**（它只削减视距，不会完全挡住），
        高度 ≥3、门、2 格高植物挡死。透明墙体（玻璃幕墙等）仍然坚实（阻挡
        移动与弹道）但不阻断视线——因此隔着幕墙可以看到对面的地形、液体与
        异象。黑烟是「类墙体」气体，浓度足够时同样挡死视线；灰尘云的视野衰减
        只在玩家的视野预算里生效（见 _sight_reaches），这里保持布尔判定供异象
        感知与光照传播使用。
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        error = dx - dy
        x, y = x0, y0
        # 异象主动技能的薄雾/折面场阻断远程视线与弹道（core/enemy_skills）：
        # 与墙体同一判定口径，逐格检查；没有场时零开销。
        skill_blocked = (
            self._skill_sight_blockers() if hasattr(self, "_skill_sight_blockers") else set()
        )
        from ..construct_environments import light_curtain_cells
        skill_blocked = skill_blocked | light_curtain_cells(self)
        while (x, y) != (x1, y1):
            if (x, y) != (x0, y0):
                cell = self.cell(x, y)
                # 高度决定遮挡（2026-10-24）：布尔接口把高度 2 当作「可通过」，
                # 只保留完全挡死的类别。
                if self._sight_obstruction(cell)[0]:
                    return False
                if self._gas_sight_effect(cell)[0]:
                    return False
                if skill_blocked and (x, y) in skill_blocked:
                    return False
            doubled = 2 * error
            if doubled > -dy:
                error -= dy
                x += sx
            if doubled < dx:
                error += dx
                y += sy
        return True
