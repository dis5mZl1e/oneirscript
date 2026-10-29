"""鼠标路由族：on_mouse_*、左右键/悬停/滚轮与面板行点击。"""
from __future__ import annotations

import time

from textual.events import MouseDown, MouseMove, MouseScrollDown, MouseScrollUp
from textual.widgets import Static

from ...i18n import tr
from ...audio import sfx
from ...core import ABILITY_DEFINITIONS
from ...core.entities import ActionResult
from ...core.tutorial import tutorial_skip_step
from ...materials import PORTENT_DEFINITIONS, TABLE_KINDS, wall_def
from .._native import _trace_native
from ..styles import MOVE_REPEAT_MIN_SECONDS, HOLD_RELEASE_TIMEOUT, RIGHT_PANEL_MODES
from ..panels import MEMORY_FOOTER_ITEM_ROWS, TAMPER_ENTRY_ROW
from ..widgets import EventPanel, MapView

ATTACK_CONFIRMATION_SECONDS = 8.0

# 动作命令 → 语义音效事件（AudioBus.SOUND_MAP 同名键）；未列出的动作不发声。
# （第一批 29 个事件已全部接入，素材与触发条件见《音效挂点索引.md》。）
# [SFX挂点] 尚未挂音效的动作命令只剩 wait（等待，可不挂）；
# 新命令在 ACTION_SOUNDS 补一行映射即可接入。
ACTION_SOUNDS = {
    "move": "step",            # 移动（_apply 会按落脚格覆写为液体/植物/冰面脚步）
    "throw": "throw",
    "throw_target": "throw",  # 瞄准投掷（同一件离手声）
    "spray_fire": "fire",
    "spray_target": "fire",
    "fire": "fire",
    "fire_assisted": "fire",   # 辅助瞄准发射（同一把枪声）
    "drop": "throw",           # 放下显化物（复用落地声）
    "pickup": "pickup",
    "collect_items": "pickup",
    "take_from": "pickup",     # 台面取物
    "put_on_table": "throw",   # 放到台面（台面落物声）
    "descend": "descend",
    "backtrack": "backtrack",  # 层间返回（上浮）
    "finish_run": "finish",
    "open": "open",            # 开门/推墙
    "uproot_plant": "uproot",  # 拔植物
    "equip": "equip",          # 穿上携带意象
    "unequip": "equip",        # 脱下（同一声金属扣）
    "toggle_equip": "equip",   # 穿/脱切换
    "use": "use_potion",       # 使用易逝物
    "choose_npc_option": "interact",  # NPC 对话选项确认
    "choose_event_option": "interact",  # 事件选项确认
    # ⚠️ interact 不在此表：打开对话的音效在 _apply_interact / _apply 叠加层里
    # 按「NPC 对话 vs 事件对话」区分（npc / interact 两种）。
}



from ..aiming import AimingMixin

class MouseRoutingMixin:
    """鼠标路由族：on_mouse_*、左右键/悬停/滚轮与面板行点击。"""

    def _left_click(self, target: tuple[int, int], ctrl: bool = False) -> None:
        self._panel_enter_mode = None
        if self.sentence_aim is not None:
            self._cast_sentence_aim(target)
            return
        self._cancel_attack_confirmation(refresh=False)
        self.path.clear()
        self.observe_walk_path.clear()
        self.path_click_goal = None
        if self.panel_mode == "event_dialog":
            # 点地图 = 离开对话（本次点击同时照常行动，与旧行为一致）。
            self._close_event_dialog_state()
            self.panel_mode = self._default_panel_mode()
        state = self.session.state
        if self.aiming:
            if self._aim_ammo_status() != 'ready':
                self.cancel_aim()
                self._begin_path_click(target)
                return
            else:
                self.confirm_aim(target)
                return
        if ctrl:
            self.pinned_target = None if self.pinned_target == target else target
            if target not in self.shortcut_targets:
                self.shortcut_targets.append(target)
            self.panel_mode = "actions"
            self.refresh_view()
            return
        # Map focus and the sidebar's current page are independent. A click
        # can control the world without resetting the other half of the UI.
        if target == (state.player.x, state.player.y):
            if any((entry.x, entry.y) == target for entry in state.world_items):
                # 自己脚下这格：左键＝尝试拾取（多件时开勾选面板）。
                self.try_pickup(target)
            elif any(
                not event.resolved
                and max(abs(event.x - state.player.x), abs(event.y - state.player.y)) <= 1
                for event in state.events
            ):
                # 脚下的异常地点（或紧贴的一格，含斜向）：与左键点那一格同一条路径，
                # interact 自己会挑最近的一个未回应地点。
                self._apply_interact()
            elif state.cell(*target).plant:
                # 站在植物上左键自己所在格：把这格植物拔掉。
                self._apply("uproot_plant")
            self.refresh_view()
            return
        dx, dy = target[0] - state.player.x, target[1] - state.player.y
        if max(abs(dx), abs(dy)) <= 1:
            entity = state.entity_at(*target)
            if entity and entity is not state.player:
                self._confirm_or_attack(target)
            elif any(not event.resolved and (event.x, event.y) == target for event in state.events):
                self._apply_interact()
                self.refresh_view()
            elif any((entry.x, entry.y) == target for entry in state.world_items) and state.cell(*target).wall_kind not in TABLE_KINDS:
                # 相邻格上的掉落物：直接走过去并捡起（台面上的东西走不上去，
                # 走相邻取物分支，见下）。
                self.facing = (max(-1, min(1, dx)), max(-1, min(1, dy)))
                self.pickup_goal = target
                self._move_player(*self.facing)
                self.refresh_view()
            elif any((entry.x, entry.y) == target for entry in state.world_items) and state.cell(*target).wall_kind in TABLE_KINDS:
                # 相邻台子上放着物品：直接取走，不必先爬上台子。
                self._apply("take_from", *target)
                self.refresh_view()
            elif not state.cell(*target).solid:
                self.facing = (max(-1, min(1, dx)), max(-1, min(1, dy)))
                self._move_player(*self.facing)
                self.refresh_view()
            elif state.cell(*target).solid:
                self._apply("open", *target)
                self.refresh_view()
            return
        self._begin_path_click(target)

    def _begin_path_click(self, target):
        state = self.session.state
        if not (0 <= target[0] < state.width and 0 <= target[1] < state.height):
            # 视口理论上有界，但兜底：边界外没有生成地形 = 维持旧的「取消寻路」。
            self._cancel_unreachable_path()
            self.refresh_view()
            return
        # 黑暗未知格（2026-10-24 玩家优化 2）：按空地寻路**接近**——
        # 不用真实地形决定「台边落脚点」（那会泄露未探索地形），
        # 路径中间撞到真实障碍由 _follow_path 停下，中途不重算。
        # 已知格（视野/记忆/全图口径）照旧走下面的完整判定。
        # ⚠️ 只有三层信息开启（雾口径生效）时才有「黑暗未知」：旧档全图可见
        # （map_memory 关）或全图地形增强开时，视野外的台子照旧走台边落脚点
        # 分支——点远程台面不能退化成取消。
        fogged = (bool(getattr(state, 'map_memory_enabled', False))
                  and not bool(getattr(state, 'terrain_known', False)))
        unknown_target = fogged and state.cell_knowledge(*target).status == 'unknown'
        # 远处格：若上面有掉落物，记下目标，走到后自动捡起。
        self.pickup_goal = target if any((entry.x, entry.y) == target for entry in state.world_items) else None
        # 「点击可寻路」的固体（石台/木桌子，见 materials.WallDef.path_clickable）：
        # 它们坚实不可通行，而 A* 的目标格必须可通行——直接拿它当终点只会得到空路径，
        # 表现为「点了台子毫无反应、寻路当场放弃」。改以台边最近的落脚点为终点，
        # 走到那里被挡住后由 _resolve_path_click_goal 回应台面的事件或取走显化物。
        target_cell = state.cell(*target)
        component = state.circuit_node_at(*target)
        circuit_control = component and component[2]["op"] in {"toggle", "pulse"}
        scavenge_control=any(e.x==target[0] and e.y==target[1] and
                             any(o.get('realm_scavenge') for o in e.options) for e in state.events)
        if (target_cell.solid and not unknown_target
                and (wall_def(target_cell.wall_kind).path_clickable
                     or wall_def(target_cell.wall_kind).pushable or circuit_control or scavenge_control)):
            standby = self._path_click_standby(target)
            click_goal, waypoint = target, standby
            self.pickup_goal = None
        else:
            click_goal, waypoint = None, target
        # 部分信息寻路：只把「看得见的格子」上的生物当障碍——视野外默认没有
        # 不可见物体（如生物），路径照常给出；真走到那里撞上了，_follow_path
        # 会停下（见下）。地形与墙体仍是完整已知的（视野外保留墙体记忆）。
        # 点击黑暗未知目标时未探索格按空地放行（接近语义，撞墙即停）。
        path = state.path_to(*waypoint, known_cells=state.visible_cells(),
                             unknown_passable=unknown_target) if waypoint else []
        if path:
            self.begin_auto_walk(path)
            self.path_click_goal = click_goal
        else:
            self._cancel_unreachable_path()
        # 无论是否找到路径都刷新：panel_mode 可能已切换（如覆盖面板被取消）。
        self.refresh_view()

    def _path_click_standby(self, target: tuple[int, int]) -> tuple[int, int] | None:
        """为「点击可寻路」的固体挑落脚点：它周围最近的、能站人的空格。

        走不到台面本身，就以台边的落脚点为寻路终点（目标格可被实体占据，
        所以这里只排除地形与实体，不排除「有异象站着」——那属于走过去再说）。
        """
        state = self.session.state
        player = (state.player.x, state.player.y)
        best: tuple[int, int] | None = None
        best_distance = 1 << 30
        pushable = wall_def(state.cell(*target).wall_kind).pushable
        known_cells = state.visible_cells()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = target[0] + dx, target[1] + dy
                if not (0 <= nx < state.width and 0 <= ny < state.height):
                    continue
                cell = state.cell(nx, ny)
                if cell.solid and cell.wall_kind != "门":
                    continue
                if state.entity_at(nx, ny) is not None:
                    continue
                if pushable:
                    if state.cell(*target).wall_kind == "理念立方体" and dx and dy:
                        continue
                    tx, ty = target[0] - dx, target[1] - dy
                    if not (0 <= tx < state.width and 0 <= ty < state.height):
                        continue
                    if state.cell(tx, ty).solid or state.entity_at(tx, ty) is not None:
                        continue
                path = state.path_to(nx, ny, known_cells=known_cells)
                if (nx, ny) != player and not path:
                    continue
                distance = len(path)
                if distance < best_distance:
                    best_distance = distance
                    best = (nx, ny)
        return best

    def _resolve_path_click_goal(self) -> None:
        """走到（或被挡住）后结算「点击可寻路」的目标：回应事件、取走台面显化物。

        只处理已经站到台边的目标（相邻才算数），避免路被别的障碍从中截断时误触发。
        """
        goal = self.path_click_goal
        self.path_click_goal = None
        if goal is None or self.observe_mode:
            return
        state = self.session.state
        if max(abs(goal[0] - state.player.x), abs(goal[1] - state.player.y)) > 1:
            return
        if any(not event.resolved and (event.x, event.y) == goal for event in state.events):
            self._apply_interact()
        elif any((entry.x, entry.y) == goal for entry in state.world_items):
            self._apply("take_from", *goal)
        elif state.circuit_node_at(*goal) or wall_def(state.cell(*goal).wall_kind).pushable:
            self._apply("open", *goal)

    def _act_on_player_cell(self) -> bool:
        """行动（Enter 键 / 底栏「Enter 行动」）：只处理相邻事务，不碰脚下。

        与 G（拾取）明确分工：**Enter 绝不拾取脚下的显化物、也不结算脚下的
        异常地点**——脚下的事走过去/按 G 处理。它只做两件事，且都在相邻范围内
        （切比雪夫距离 1）：
        1. 回应相邻的未解异常地点（地点优先，它更稀奇且会解算奖励）；
        2. 取走相邻台子（木桌子/石台）台面上的显化物。
        两者都没有时，若脚下有植物则拔掉（这是纯脚下动作，与拾取无关，保留）。
        返回是否真的发生了动作，供调用方判断要不要退化成别的语义（如「结束入梦」）。
        """
        state = self.session.state
        position = (state.player.x, state.player.y)
        has_adjacent_event = any(
            not event.resolved
            and max(abs(event.x - position[0]), abs(event.y - position[1])) <= 1
            for event in state.events
        )
        has_surface_item = state.adjacent_table_with_item() is not None
        has_adjacent_npc = any(
            entry.relation == "稳定意识" and entry.integrity > 0
            and max(abs(entry.x - position[0]), abs(entry.y - position[1])) <= 1
            for entry in state.enemies
        )
        has_circuit_control = any(n["op"] in {"toggle", "pulse"}
                                  and max(abs(n["pos"][0]-position[0]), abs(n["pos"][1]-position[1])) == 1
                                  for b in state.circuit_boards for n in b["nodes"].values())
        if has_adjacent_event or has_surface_item or has_adjacent_npc or has_circuit_control:
            self._apply_interact()
            return True
        if state.cell(*position).plant:
            # 相邻无事可做时才退到「拔掉脚下的植物」——纯脚下动作，与拾取无关。
            self._apply("uproot_plant")
            return True
        return False
    def _right_click(self, target: tuple[int, int]) -> None:
        if self.aiming:
            self._left_click(target)
            return
        self.path.clear()
        self.observe_walk_path.clear()
        actions = self._actions_for(target)
        # [SFX挂点] 右键打开上下文菜单：建议 ui_click（界面操作）。
        self.context_menu_target = target
        if len(actions) == 1 and actions[0] != "观察":
            action = actions[0]
            if action.startswith("攻击"):
                self._confirm_or_attack(target)
            elif action == "交谈":
                # 稳定意识（NPC）：右键菜单里的「交谈」与左键同路径——直接进对话。
                self._confirm_or_attack(target)
            elif action == "拾取":
                self.try_pickup(target)
                self.refresh_view()
            elif action == "回应":
                self._apply_interact()
                self.refresh_view()
            elif action == "移动":
                self._left_click(target)
            elif action == "打开":
                self._apply("open", *target)
                self.refresh_view()
        else:
            # [SFX] 右键打开上下文菜单（真正切到 actions 面板时才响）。
            if self.config.get("sfx_enabled"):
                sfx.play("ui_click", volume=int(self.config.get("sfx_volume")) / 10)
            self.panel_mode = "actions"
            self.refresh_view()

    def _panel_visual_row(self, offset_y: int, widget=None) -> int:
        """面板点击 → **可视行号**（-1 = 命中空白）。

        `_panel_row_at` 只给条目序号，但点击要拿的是行号本身——
        「行 → 条目键」的快照 `_panel_row_keys` 是按可视行索引的。
        """
        rows = self._panel_rows
        if not rows:
            return -1
        try:
            if widget is not None:
                scroll_y = int(widget.scroll_offset.y)
            else:
                scroll_y = int(self.query_one("#panel").scroll_offset.y)
        except Exception:
            scroll_y = 0
        y = offset_y + scroll_y
        if y < 0:
            return -1
        if y >= len(rows):
            # 容错：只放宽一格（视窗底边框），再往下就是真的超出内容。
            return len(rows) - 1 if y == len(rows) else -1
        return y

    def _panel_row_at(self, offset_y: int, widget=None) -> int:
        """面板点击 → 条目序号（-1 = 装饰行/命中空白）。

        判定规则刻意放宽，解决「行囊里有些物体左右键点不中」：
        - **横向不设限**：条目行整行可点（含左侧的 ▶ 标记区与名称右侧的空白），
          只要纵向落在那一行即可。旧实现其实也没判 x，但行映射一旦包含
          「缩进的注释行」就极易差一行；这里统一由 ``_panel_rows`` 保证
          「可视行 → 条目」的精确对应。
        - **纵向容错一行**：点到最后一条的下沿（offset 恰好等于视窗高度）
          也当作点在最后一条上——鼠标划过底边框时不再「点了没反应」。
        """
        rows = self._panel_rows
        if not rows:
            return -1
        try:
            if widget is not None:
                scroll_y = int(widget.scroll_offset.y)
            else:
                scroll_y = int(self.query_one("#panel").scroll_offset.y)
        except Exception:
            scroll_y = 0
        y = offset_y + scroll_y
        if y < 0:
            return -1
        if y >= len(rows):
            # 容错：只放宽一格（视窗底边框），再往下就是真的超出内容。
            if y == len(rows) and rows:
                return rows[-1]
            return -1
        return rows[y]

    def handle_panel_right_click(self, event: MouseDown) -> None:
        self._select_input_region('overlay' if getattr(event.control, 'id', None) == 'map-overlay' else 'panel')
        if self.layer_observation is not None:
            if getattr(getattr(event, 'control', None), 'id', None) == 'map-overlay':
                self._layer_close_detail()
            event.stop()
            return
        """右键面板条目：行囊打开该物品的左侧菜单，观测打开意象详情。"""
        if getattr(self, 'controls_help_open', False):
            event.stop()
            return
        self._dismiss_transient()
        widget = getattr(event, "control", None)
        if getattr(widget, "id", None) == "map-overlay":
            # 覆盖面板（物品菜单/意象详情/格子详情）已打开时右键＝点击其他地方，只取消它。
            self.close_item_menu()
            self.close_anomaly_detail()
            self.close_cell_detail()
            if self.panel_mode == "event_dialog":
                # 对话悬浮面板同理：右键＝离开对话。
                self._close_event_dialog_state()
                self.panel_mode = self._default_panel_mode()
                self.refresh_view()
            return
        # 与左键一致：offset 是可视行，叠加面板滚动量才对应真实行（判定见 _panel_row_at）。
        index = self._panel_row_at(event.offset.y)
        if index < 0:
            return
        if self.panel_mode in ("inventory", "equipment"):
            self._open_item_menu(index)
        elif self.panel_mode == "catalog":
            # 观测面板按种类聚合，右键展开「同名个体逐一分列」的详情。
            self._open_anomaly_detail(index)

    def handle_map_mouse_down(self, map_view: MapView, event: MouseDown) -> None:
        self._keys_handled_in_on_key.clear()
        self._dismiss_transient()
        if not self._left_overlay_blocks_interrupt():
            if self._left_panel_open():
                self._dismiss_left_panel()
            self._select_input_region('map')
        if self.layer_observation is not None:
            self._layer_point(map_view.cell_from_offset(event.offset))
            if event.button == 3 and self.observe_cursor is not None:
                self.open_cell_detail(self.observe_cursor)
                self._sync_layer_observation_ui()
            event.stop()
            return
        if self._active_tamper_editor() is not None and self._active_tamper_editor().map_preview:
            self._tamper_preview_point(map_view.cell_from_offset(event.offset))
            event.stop()
            return
        if self.world_tamper_editor is not None:
            # 地图篡改面板打开时点地图 = 返回：必须同时清掉 editor 和 panel_mode。
            # 旧实现只让点击落到普通地图流程，editor 残留但 panel_mode 已被改成
            # world，此后右侧面板的点击都会被「篡改中」分支吞掉，表现为按钮全部失效。
            self.close_world_tamper_editor()
            event.stop()
            return
        if getattr(self, "_self_audit_visible", None) and self._self_audit_visible():
            # 点地图 = 收起自我察觉面板（点击行为本身继续照常执行）。
            self._close_self_audit(refresh=False)
        if (getattr(self, 'controls_help_open', False) or getattr(self, 'qol_confirmation', None)
                or getattr(self, 'qol_searching', False)):
            event.stop()
            return
        if self.tamper_editor is not None:
            # 篡改编辑期间点击地图：只收起面板，这一下不落地——不走路、不攻击、
            # 不交易（规格 §4.3「避免编辑点击穿透」）。
            event.stop()
            self.handle_tamper_mouse("map", event.offset.y, event.offset.x,
                                     event_kind="down", button=event.button)
            return
        if self.equipment_choice is not None:
            event.stop()
            return
        if getattr(self, "_floor_transition", None) is not None:
            # 演出中点击 = 跳过动画（与任一键同语义，设计文档 §2.3）。
            self._finish_floor_transition(suppress_wipe=False)
            event.stop()
            return
        self._panel_enter_mode = None
        self._dismiss_transient()
        # 左侧覆盖面板打开时：左键地图只关面板、不行动（要先退出再点第二次）。
        # 替换洞察/替换记忆不可被打断——它们只认自己的选中确认，点击一律吞掉。
        # 同样靠「关了就 return」消耗掉本次点击，不需要额外的「下次才生效」标记。
        # （2026-10-11：浮层自适应后不再铺满整块地图，点到浮层外的格子会真的
        # 落到 #map，因此这一层必须早于普通地图点击处理，保持「一次点击退出」
        # 的既有手感。2026-10-26：这里不再牵涉 ~ 锁定/解锁。）
        if self._active_left_overlay() is not None:
            if self._left_overlay_blocks_interrupt():
                event.stop()
                return
            self._close_active_left_overlay()
            self.refresh_view()
            event.stop()
            return
        # 2026-10-26 玩家定稿：点击地图不再解除 ~ 锁定——锁定只冻结右栏页面，
        # 点击恢复普通行为（能走就走、能行动就行动），右栏页由手动键鼠切换。
        _trace_native(
            f"DreamApp.on_mouse_down control={type(getattr(event, 'control', None)).__name__} "
            f"offset={event.offset} button={event.button}"
        )
        target = map_view.cell_from_offset(event.offset)
        if not target:
            return
        if self.observe_mode:
            # 观察模式：左键＝让 ? 无视障碍走最短格子（寻路节拍推进，自己不动、
            # 时间静止）。右键＝打开 ? 所在格（或点中的格）的格子详情。
            if event.button == 1:
                self._observe_walk_to(target)
            elif event.button == 3:
                self.open_cell_detail(target)
            event.stop()
            return
        if event.button == 1:
            # 修饰键用 Alt（终端收不到 Ctrl，用户规定 2026-10-15）；
            # Ctrl 位保留兼容个别能上报它的终端。
            self._left_click(target, ctrl=bool(getattr(event, "ctrl", False) or getattr(event, "alt", False)))
        elif event.button == 2:
            self.pinned_target = None if self.pinned_target == target else target
            self.panel_mode = "actions"
            self.refresh_view()
        elif event.button == 3:
            # 右键＝打开该格的完整信息面板（不执行移动/破坏/发射）。
            self.open_cell_detail(target)
        event.stop()
    def on_mouse_down(self, event: MouseDown) -> None:
        self._note_activity()
        self._keys_handled_in_on_key.clear()
        self._dismiss_transient()
        _trace_native(
            f"DreamApp.generic_mouse_down control={type(event.control).__name__} "
            f"screen=({event.screen_x},{event.screen_y}) button={event.button}"
        )
        if isinstance(event.control, MapView):
            self.handle_map_mouse_down(event.control, event)
        elif getattr(event.control, 'id', None) == 'map-pane':
            if not self._modal_menu_open(allow_inspection=True):
                self._dismiss_left_panel()
                self._select_input_region('map')
        elif getattr(event.control, 'id', None) == 'side-pane':
            self._select_input_region('panel')

    def refresh_hover_only(self) -> None:
        """鼠标移动的轻量刷新：只更新悬停观察区。

        悬停文本只依赖悬停格与玩家状态，不涉及地图/面板/状态栏——
        全量 refresh_view 会在鼠标掠过地图时以极高频率重建整块 UI，
        这是卡顿的主要来源。
        """
        try:
            hover_widget = self.query_one("#hover-info", Static)
            width = hover_widget.content_size.width or 44
            hover_widget.update(self._sidebar_context_text(self.session.state, width))
            self._refresh_map_hints()
        except Exception:
            return

    def handle_map_mouse_move(self, map_view: MapView, event: MouseMove) -> None:
        if self._active_tamper_editor() is not None:
            return
        if getattr(self, 'controls_help_open', False):
            return
        if self.tamper_editor is not None:
            # 编辑期间地图悬停冻结：落点/辅助路径不跟着鼠标跑，视线留在正文上。
            return
        if self.observe_mode:
            # 观察模式：右上角的读数固定在 ? 上（「观察:(x,y)」），鼠标掠过地图
            # 不改落点——? 由键盘/点击驱动，这里只保证读数不会被鼠标带走。
            if self.hover_cell != self.observe_cursor:
                self.hover_cell = self.observe_cursor
                self.refresh_hover_only()
            return
        self.hover_cell = map_view.cell_from_offset(event.offset)
        if self.sentence_aim is not None:
            if self.hover_cell is not None:
                self.sentence_aim['cursor'] = self.hover_cell
            self._refresh_cursor_only()
            return
        if self.target_assist and self.hover_cell:
            # 目标辅助：与左键点击完全同款的寻路（8 向 A*）；
            # 不可达时 path_to 返回空 = 不显示路径。
            # 同格重复事件由 _refresh_assist_path 的签名缓存挡掉。
            self._refresh_assist_path(self.hover_cell)
        elif self.target_assist:
            self.assist_path = []
            self._assist_cache = None
        self._refresh_cursor_only()
    def handle_panel_mouse_down(self, event: MouseDown, panel: Static | None = None) -> None:
        widget = panel if panel is not None else getattr(event, 'control', None)
        self._select_input_region('overlay' if getattr(widget, 'id', None) == 'map-overlay' else 'panel')
        if self._inspection_active() and getattr(widget, 'id', None) != 'panel':
            event.stop()
            return
        if self._layer_panel_mouse(event, panel):
            return
        """面板鼠标：左键 = 使用/穿戴/激活（同 Enter）；Shift+左键 = 展开/收起该条。

        右侧面板与地图上层覆盖面板（行囊）行为完全一致；
        滚动偏移取自实际被点击的面板控件（两者滚动互不同步）。

        ``panel`` 是真正接到事件的控件（由 EventPanel.on_mouse_down 传入）。
        不能用 ``event.control`` 判断：覆盖面板打开时点击地图区域，pilot/原生
        事件的 control 仍是 MapView，用它判断会把覆盖面板的点击当成地图点击。

        - 左键：等价于把选中行移到该条并按 Enter——行囊里是使用或穿戴、
          已穿戴的再点一次即脱下；操作界面里是激活构想或执行目标操作；
          观测/征兆/洞察里则展开该条的注释。
        - Shift+左键：只切换该条的展开/收起，不触发使用（避免误用物品）。
        - \\ 键仍是全局一键收起/展开。
        """
        if (getattr(self, 'controls_help_open', False) or getattr(self, 'qol_confirmation', None)
                or getattr(self, 'qol_searching', False)):
            event.stop()
            return
        if self._floor_transition_skip():
            # 演出中点击面板 = 跳过动画（与地图点击同一语义，设计文档 §2.3）。
            event.stop()
            return
        # 瞄准/施放态（2026-10-24 玩家优化 1）：面板区域不再响应条目激活——
        # 点地图 = 在对应位置释放（_left_click → confirm_aim/_cast_sentence_aim），
        # 点面板 = 取消本次动作（与 Esc 同语义，零消耗）。面板在瞄准中显示的
        # 世界条目没有「瞄着它用」的语义，旧路径会把选中挪走却打不出手。
        if self.sentence_aim is not None:
            self._cancel_sentence_aim()
            self.refresh_view()
            event.stop()
            return
        if self.aiming:
            self.cancel_aim()
            self.refresh_view()
            event.stop()
            return
        self._dismiss_transient()
        widget = panel if panel is not None else getattr(event, "control", None)
        widget_id = getattr(widget, "id", None)
        if widget_id == 'panel' and self._sidebar_navigation_allowed():
            if self.panel_subtab_click(self._panel_visual_row(event.offset.y), int(event.offset.x)):
                event.stop()
                return
        if self._world_tamper_side_active() and widget_id == 'panel':
            event.stop()
            if event.button == 1:
                row = self._panel_visual_row(event.offset.y)
                inset = widget.content_region.x - widget.region.x
                self._tamper_side_click(self._tamper_side_pointer_key(row, event.offset.x-inset))
            return
        if self.tamper_editor is not None and widget_id != "tamper-overlay":
            # 编辑期间点击对话/其他面板：不选选项、不交易，只收起篡改面板
            # （规格 §4.3 防穿透；篡改面板自己的点击由 TamperOverlayPanel 处理）。
            inset_x = (widget.content_region.x - widget.region.x
                       if widget_id == 'map-overlay' else 2)
            self.handle_tamper_mouse(str(widget_id), event.offset.y - 2, event.offset.x - inset_x,
                                     event_kind="down", button=event.button)
            event.stop()
            return
        if self.world_tamper_editor is not None:
            # 地图篡改面板（docs §15.7）：点击右侧面板行 = 选字词/切目标槽；
            # 不做对话穿透（面板开着时地图点击先收面板）。
            event.stop()
            if event.button == 1 and widget_id == 'panel':
                row = self._panel_visual_row(event.offset.y)
                keys=getattr(self,'_panel_row_keys',())
                key = keys[row] if 0 <= row < len(keys) else None
                self._world_tamper_click(key)
            return

        if (not self.home_mode and widget_id == 'panel'
                and self._panel_subpage_ids()):
            visual_row = self._panel_visual_row(event.offset.y)
            # 顶部若干行 = 同一按钮界面内的分层页签：点击切换。
            if 0 <= visual_row and any(row == visual_row for row, _s, _e, _p in
                                       getattr(self, '_panel_subtab_hits', ())):
                if self.panel_subtab_click(visual_row, int(event.offset.x)):
                    event.stop()
                    return
        if self.equipment_choice is not None:
            if widget_id == 'map-overlay' and event.button == 1:
                index = getattr(self, '_equipment_choice_rows', {}).get(event.offset.y - 2)
                if index is not None:
                    self._choose_equipment_action(index)
            event.stop()
            return
        # 洞察之镜面板：左键点行 = 选定该洞察并消耗镜子。
        if self.mirror_index is not None and widget_id == "map-overlay":
            line = event.offset.y - 2
            # 渲染口径（_mirror_select_text）：标题 1 行 + 空行 1 行，之后每个
            # 候选占 **2 行**（名字 + 缩进说明）。旧判定按每候选 1 行硬编码，
            # 点候选 1 会选中候选 2、点候选 2/3 落空——鼠标永远选不对也确认不了
            # （2026-10-12 修复）。名字行或说明行都算选这个候选。
            row = line - 2
            if 0 <= row < len(self.mirror_rolls) * 2:
                picked = self.mirror_rolls[row // 2]
                self._apply("choose_mirror_insight", self.mirror_index, picked)
                self.mirror_index = None
            event.stop()
            return
        # 喷射弹药选择浮层：左键点行 = 选用该容器并进入瞄准。
        if getattr(self, "spray_select", None) is not None and widget_id == "map-overlay":
            y = event.offset.y - 2
            for line, inv_idx in self._spray_rows:
                if line == y:
                    self._choose_spray_ammo(inv_idx)
                    break
            event.stop()
            return
        # §8 S23 青灯祭品浮层：左键点行 = 勾选/取消该件祭品。
        if self.lens_offer_scene and widget_id == "map-overlay":
            y = event.offset.y - 2
            for line, inv_idx in self._lens_offer_rows:
                if line == y:
                    self._lens_offer_toggle(inv_idx)
                    self.refresh_view()
                    break
            event.stop()
            return
        # 容器浮层：左键点「盛装/倒出」行＝执行对应操作（行号在渲染时登记）。
        if getattr(self, "container_index", None) is not None and widget_id == "map-overlay":
            rows = getattr(self, "_container_action_rows", None)
            if rows is not None:
                # offset 含边框与内边距（各 1 行），内容行 = offset.y - 2。
                y = event.offset.y - 2
                if y == rows[0]:
                    self._apply("container_fill", self.container_index)
                elif y == rows[1]:
                    self._apply("container_pour", self.container_index)
            event.stop()
            return
        # 洞察替换面板打开时：左键点条目行 = 把光标移到那一条（再 Enter/再点一次替换），
        # 在确认放弃态下点面板任意处 = 确认放弃；点在内容之下 = 请求放弃（进二次确认）。
        if self.insight_replace_target is not None and widget_id == "map-overlay":
            if self.insight_replace_confirm_discard:
                self.activate_insight_replace()
                event.stop()
                return
            rows = self._insight_replace_rows
            y = event.offset.y - 2  # offset 含边框与内边距（各 1 行）
            if 0 <= y < len(rows) and rows[y] >= 0:
                index = rows[y]
                if index == self.insight_replace_cursor:
                    # 再点同一条＝确认替换它（与 Enter 一致）。
                    self.activate_insight_replace()
                else:
                    self.insight_replace_cursor = index
                    self.refresh_view()
            elif y >= len(rows):
                # 点在内容区之下：等同于按 Esc——进入放弃二次确认，而不是静默退出。
                self.request_discard_insight()
            event.stop()
            return
        # 记忆碎片替换面板：与上面洞察替换面板同构（同一块 #map-overlay 浮层）。
        if self.memory_replace_target is not None and widget_id == "map-overlay":
            if self.memory_replace_confirm_discard:
                self.activate_memory_replace()
                event.stop()
                return
            rows = self._memory_replace_rows
            y = event.offset.y - 2  # offset 含边框与内边距（各 1 行）
            if 0 <= y < len(rows) and rows[y] >= 0:
                index = rows[y]
                if index == self.memory_replace_cursor:
                    # 再点同一条＝确认替换它（与 Enter 一致）。
                    self.activate_memory_replace()
                else:
                    self.memory_replace_cursor = index
                    self.refresh_view()
            elif y >= len(rows):
                # 点在内容区之下：等同于按 Esc——进入放弃二次确认。
                self.request_discard_memory()
            event.stop()
            return
        # 物品菜单打开时：左键点功能行 = 执行对应功能（行映射用 _menu_rows）；
        # 点在菜单内容区之下（覆盖面板的空白处）＝ 取消菜单，等同 Q/Esc；
        # 点在边框/装饰行（内容区之上）＝ 视为点在菜单上，保持打开。
        # 注意覆盖面板铺满整块地图，「点击地图（范围外）」实际命中的也是它。
        if self.item_menu_target is not None and widget_id == "map-overlay":
            rows = self._menu_rows
            # offset 含边框与内边距（各 1 行），内容行 = offset.y - 2。
            y = event.offset.y - 2
            if 0 <= y < len(rows):
                action_key = rows[y]
                if isinstance(action_key, str):
                    self.activate_item_menu(action_key)
            elif y >= len(rows):
                self.close_item_menu()
            event.stop()
            return
        # 意象详情（左侧覆盖面板）：左键落在内容行＝把光标移到该行；
        # 落在内容之下＝关闭。内容行要加 detail_scroll 折算成逻辑行——渲染是
        # 滚动切片（panels._anomaly_detail_text 用 lines[scroll:scroll+viewport]），
        # 不加偏移滚动后点击会选错行；「内容之下」也要跟视窗内的显示行数比，
        # 旧口径拿逻辑总行数比屏幕行，内容超长时点底部永远关不掉（2026-10-12）。
        if self.anomaly_detail_target is not None and widget_id == "map-overlay":
            y = event.offset.y - 2
            shown = min(self._anomaly_detail_viewport(),
                        max(0, self._detail_line_count - self.detail_scroll))
            if 0 <= y < shown:
                self.detail_cursor = y + self.detail_scroll
                self._follow_anomaly_detail()
                self.refresh_view()
            elif y >= shown:
                self.close_anomaly_detail()
            event.stop()
            return
        # 格子详情（左侧覆盖面板）：同一套手感——点内容行移动光标，点下方关闭。
        # 滚动折算与关闭口径与上分支同（2026-10-12 修复）。
        if self.cell_detail_target is not None and widget_id == "map-overlay":
            y = event.offset.y - 2
            shown = min(self._anomaly_detail_viewport(),
                        max(0, self._detail_line_count - self.detail_scroll))
            if 0 <= y < shown:
                row = y + self.detail_scroll
                again = row == self.detail_cursor
                self.detail_cursor = row
                self._follow_anomaly_detail()
                if again:
                    # 再击已选中的条目 = 进入子详情/展开（与拾取面板同款两段式）；
                    # 首击只移动光标，退出与进入都不消耗游戏输入（docs §16.6）。
                    self._cd_activate_row()
                self.refresh_view()
            elif y >= shown:
                self.close_cell_detail()
            event.stop()
            return
        # 对话面板（左侧悬浮，NPC/复合事件共用）：左键两段式——首击只选中
        # （▶ 移到该项），已选中的项再击才执行（2026-09-18 应用户要求）；
        # 点在内容之下＝离开对话（同 Esc）。
        # 拾取面板（map-overlay 浮层）：光标所在条上左键 = 切换勾选；
        # 点其他条 = 光标移到那一条。点条目区之外 = 关闭面板。
        if self.pickup_target is not None and widget_id == "map-overlay":
            entries = self.pickup_candidates(*self.pickup_target)
            metadata=event.style.meta
            action=metadata.get('pickup_action')
            item_index=metadata.get('pickup_index')
            if action=='confirm':
                self.activate_pickup()
            elif action=='cancel':
                self.close_pickup()
            elif isinstance(item_index,int) and 0 <= item_index < len(entries):
                if item_index == self.pickup_cursor:
                    self.toggle_pickup_selection()
                else:
                    # 首击只移动光标；再点同一条才勾选（与 Enter 手感一致）。
                    self.pickup_cursor = item_index
            else:
                self.close_pickup()
            self.refresh_view()
            event.stop()
            return
        if self.panel_mode == "event_dialog" and widget_id == "map-overlay":
            # offset 含边框与内边距：用控件自己的内容区偏移算，别写死 2 行
            # （不同边框/主题/缩放下边框与 padding 不一定各 1 行）。
            inset_y = int(widget.content_region.y - widget.region.y)
            y = event.offset.y - inset_y
            rows = getattr(self, "_dialog_rows", [])
            if 0 <= y < len(rows) and rows[y] == TAMPER_ENTRY_ROW:
                # 点篡改提示行 = 按篡改键（规格 §4.1：入口是可点击的）。
                self.open_tamper_editor()
            elif 0 <= y < len(rows) and rows[y] >= 0:
                self._click_dialog_option(rows[y])
            elif y >= len(rows):
                self._close_event_dialog_state()
                self.panel_mode = self._default_panel_mode()
                self.refresh_view()
            event.stop()
            return
        rows = self._panel_rows
        if not rows:
            return
        index = self._panel_row_at(event.offset.y, widget=widget if widget_id == "map-overlay" else None)
        # 2026-10-24 玩家定稿：点「构筑·装备」页的联想盘示意图直接进入编辑器；
        # -4 是盘面图形与「[ 编辑联想盘」提示行的专用行标记。
        if index == -4:
            if (self.panel_mode == 'equipment' and self._panel_subpage_id() != 'memory'
                    and self._sidebar_navigation_allowed()):
                self.open_board_editor()
                event.stop()
            return
        if index < 0:
            return
        # 条目键走**渲染时的快照**（_panel_row_keys 与 _panel_rows 逐行对齐）：
        # 重算会在「目标操作」条数变化时被算成 None，左键就静默失效了。
        visual_row = self._panel_visual_row(
            event.offset.y, widget=widget if widget_id == "map-overlay" else None
        )
        keys = getattr(self, "_panel_row_keys", None) or []
        if 0 <= visual_row < len(keys) and keys[visual_row] is not None:
            key = keys[visual_row]
        else:
            key = self._panel_entry_key(index)
        if self.panel_mode == "equipment" and self._panel_subpage_id() != "memory":
            # 行映射存的是真实行囊下标：选中光标按「行囊中的携带意象」列表的
            # 位置换算，否则 ▶ 跳到别的条目、激活也会算错物品（点击错位根因）。
            equipment_indices = [i for i, item in enumerate(self.session.state.inventory) if item.slot]
            if index not in equipment_indices:
                return
            self.panel_selection = equipment_indices.index(index)
        else:
            self.panel_selection = index
        # ]+左键（] 键武装的下一次点击）：所有面板统一只切换该条展开/收起。
        if self._bracket_armed:
            self._bracket_armed = False
            self.expanded_key = None if self.expanded_key == key else key
            self.details_expanded = False  # 进入单条模式，覆盖全局展开
            self.refresh_view()
            return
        # 行囊/操作页：左键使用/穿戴/激活（等价 Enter）；观测/征兆/洞察：左键即展开。
        operable = self.panel_mode in ("inventory", "equipment", "actions", "tasks", "world", "build_overview", "self_overview", "nearby", "sidebar_detail")
        if bool(getattr(event, "shift", False)) or not operable:
            self.expanded_key = None if self.expanded_key == key else key
            self.details_expanded = False
            self.refresh_view()
            return
        self._activate_panel_selection(key_hint=key)

    def on_mouse_move(self, event: MouseMove) -> None:
        self._note_activity()
        if self.layer_observation is not None:
            # A parked editor or sidebar list must not reclaim this observer's
            # cursor/selection when the pointer crosses either widget.
            self.hover_cell = self.layer_observation.cursor
            event.stop()
            return
        editor = self._active_tamper_editor()
        if editor is not None:
            if editor.map_preview and self.hover_cell != editor.preview_cursor:
                self.hover_cell = editor.preview_cursor
                self.refresh_hover_only()
            if getattr(event.control, 'id', None) != 'panel':
                return
            if self._world_tamper_side_active():
                widget = event.control
                row = self._panel_visual_row(event.offset.y)
                column = event.offset.x - (widget.content_region.x-widget.region.x)
                key = self._tamper_side_pointer_key(row, column)
                if key and key.startswith('word:') and key[5:] != editor.word_id:
                    self._world_tamper_click(key)
                elif key and key.startswith('ctoggle:'):
                    from ...core.tamper_world import condition_ids_for
                    singles = tuple(cid for cid in condition_ids_for(editor.sentence, editor.word_id, editor.slot)
                                    if cid not in ('gently', 'forcefully'))
                    if key[8:] in singles:
                        index = singles.index(key[8:])
                        if editor.focus != 'condition' or editor.condition_cursor != index:
                            editor.focus = 'condition'
                            editor.condition_cursor = index
                            self.refresh_view()
                return
            self._update_panel_hover(event.offset.y)
            return
        if getattr(self, 'controls_help_open', False):
            return
        control = event.control
        if not self.home_mode and self.panel_mode == "board_editor":
            # 编辑器的悬停由盘面/说明区控件自己处理并 event.stop()；落到这里的
            # 是覆盖层空白处，不去动已隐藏的地图与右侧面板。
            return
        if isinstance(control, MapView):
            self.handle_map_mouse_move(control, event)
            if self.item_menu_target is not None and self._menu_hover_row is not None:
                # 光标离开菜单回到地图：清掉菜单的悬停选中。
                self._menu_hover_row = None
                self._refresh_menu_only()
            return
        if isinstance(control, EventPanel):
            # 面板悬停：光标选中（与键盘选择效果一致）——右侧面板条目
            # 移动 ▶/reverse 高亮，左侧物品菜单功能行加实心框。
            if self.hover_cell is not None:
                self.hover_cell = None
                self.refresh_hover_only()
            widget_id = getattr(control, "id", None)
            if widget_id == "map-overlay" and self.item_menu_target is not None:
                self._update_menu_hover(event.offset.y - 2)
            elif widget_id == "map-overlay" and self.anomaly_detail_target is not None:
                # 意象详情覆盖在地图上，偏移行与右侧面板的行号无关；
                # 这里不参与右侧面板的悬停选中，避免 ▶ 随覆盖面板乱跳。
                pass
            elif widget_id == "map-overlay" and self.cell_detail_target is not None:
                # 格子详情同理：不参与右侧面板的悬停选中。
                pass
            elif (widget_id == "map-overlay"
                  and getattr(self, "insight_replace_target", None) is not None):
                # 洞察替换（物品/剧情产生）：悬停即选中该条，▶ 与鼠标对齐。
                if not self.insight_replace_confirm_discard:
                    inset_y = int(control.content_region.y - control.region.y)
                    row = event.offset.y - inset_y
                    rows = getattr(self, "_insight_replace_rows", [])
                    if 0 <= row < len(rows) and rows[row] >= 0:
                        index = rows[row]
                        if index != self.insight_replace_cursor:
                            self.insight_replace_cursor = index
                            self.refresh_view()
            elif (widget_id == "map-overlay"
                  and getattr(self, "memory_replace_target", None) is not None):
                # 记忆碎片替换：同上。
                if not self.memory_replace_confirm_discard:
                    inset_y = int(control.content_region.y - control.region.y)
                    row = event.offset.y - inset_y
                    rows = getattr(self, "_memory_replace_rows", [])
                    if 0 <= row < len(rows) and rows[row] >= 0:
                        index = rows[row]
                        if index != self.memory_replace_cursor:
                            self.memory_replace_cursor = index
                            self.refresh_view()
            elif widget_id == "map-overlay" and self.panel_mode == "event_dialog":
                if self.tamper_editor is not None:
                    self.handle_tamper_mouse(widget_id, event.offset.y - 2,
                        event.offset.x - (control.content_region.x - control.region.x),
                        event_kind='move')
                else:
                    # 2026-10-28：对话（书卷/事件/NPC）悬停与 ▶ 选中对齐。
                    # 旧实现悬停完全不更新 event_dialog_cursor，鼠标停在某条上
                    # 却仍高亮别的条目；点击又只是「首击选中」，玩家会以为点击无效。
                    # 现在悬停即选中该条，随后单击同一条直接确认；键盘 ↑↓ 不受影响。
                    inset_y = int(control.content_region.y - control.region.y)
                    row = event.offset.y - inset_y
                    rows = getattr(self, "_dialog_rows", [])
                    if 0 <= row < len(rows):
                        option = rows[row]
                        if option >= 0 and option != self.event_dialog_cursor:
                            self.event_dialog_cursor = option
                            self.refresh_view()
            elif widget_id != 'map-overlay':
                self._update_panel_hover(event.offset.y)
            return
        if self.hover_cell is not None:
            # 鼠标移出地图（右侧面板/边框/空白处）：清除残留悬停，
            # 悬停区回退显示（当前）所在位置的环境。
            self.hover_cell = None
            self.refresh_hover_only()

    def _update_menu_hover(self, content_row: int) -> None:
        """左侧物品菜单：光标悬停到功能行时选中该行（实心框提示）。"""
        rows = self._menu_rows
        row = content_row if 0 <= content_row < len(rows) and isinstance(rows[content_row], str) else None
        if row == self._menu_hover_row:
            return
        self._menu_hover_row = row
        self._refresh_menu_only()

    def _refresh_menu_only(self) -> None:
        """轻量刷新：只重建物品菜单覆盖面板，不动地图与右侧面板。"""
        try:
            overlay = self.query_one("#map-overlay")
            overlay.update(self._item_menu_text(self.session.state))
        except Exception:
            return

    def _update_panel_hover(self, offset_y: int) -> None:
        """右侧面板：光标悬停到条目行时把选中移过去（与键盘 ↑↓ 等效）。"""
        if self.home_mode or self.panel_mode == "world":
            return
        index = self._panel_row_at(offset_y)
        if index < 0 or self._panel_entry_key(index) is None:
            return
        if self.panel_mode == "equipment":
            equipment_indices = [i for i, item in enumerate(self.session.state.inventory) if item.slot]
            if index not in equipment_indices:
                return
            selection = equipment_indices.index(index)
        else:
            selection = index
        if selection != self.panel_selection:
            self.panel_selection = selection
            if self.panel_mode in {'inventory', 'equipment', 'insights', 'portents', 'catalog'}:
                self._refresh_panel_selection()
            else:
                self.refresh_view()

    def _refresh_panel_selection(self) -> None:
        """Selection changes only affect sidebar content and its UI bookkeeping."""
        # 与 refresh_view 的成对顺序一致：owner/锁定瞄准的停放恢复先跑，
        # 再重建面板。否则 hover 路径在锁定瞄准/owner 切换场景下与普通刷新
        # 行为不一致（2026-10-25 独立审查发现的缺口）。
        self._sidebar_before_refresh()
        self.query_one('#panel', Static).update(self._panel_text(self.session.state))
        self._refresh_panel_help()
        self._refresh_qol()
        self._sidebar_after_refresh()
        if self._coach_enabled():
            from ...core.origin_course import observe_ui, pump
            observe_ui(self)
            pump(self.session.state)
        self._refresh_tutorial_coach()

    def _scroll_right_panel(self, event, amount: int) -> bool:
        """A wheel over the sidebar belongs to it, even with left details open."""
        if (getattr(getattr(event, 'control', None), 'id', None) != 'panel'
                or getattr(event, 'ctrl', False) or not self._sidebar_navigation_allowed()):
            return False
        if self.panel_mode == 'equipment' and self._memory_region_row_at(event):
            self._scroll_memory(-amount)
        else:
            self._scroll(amount)
        event.stop()
        return True

    def on_mouse_scroll_up(self, event: MouseScrollUp) -> None:
        self._note_activity()
        if self._scroll_right_panel(event, 1):
            return
        if self._inspection_active():
            event.stop()
            return
        if self._layer_scroll(event, -1):
            return
        if self._active_tamper_editor() is not None:
            # 篡改编辑/预览是模态层：地图与右栏的滚轮（含 Ctrl 缩放）一律不响应；
            # 浮层内的滚轮由 TamperOverlayPanel 自己转给编辑器。
            event.stop()
            return
        if self._scroll_self_audit(event, -1):
            return
        if self._scroll_layer_info(event, -1):
            return
        if getattr(self, 'controls_help_open', False):
            event.stop()
            return
        if self.panel_mode == 'home_newgame':
            self.query_one('#newgame-scroll').scroll_relative(y=-3, animate=False)
            return
        if not self.home_mode and self.panel_mode == "board_editor":
            # 编辑器：滚轮只滚说明区（盘面 6 行恒定可见，不跟着滚）。
            # Ctrl+滚轮的地图缩放也不放行——#layout 已隐藏，改了玩家看不见。
            self.board_editor_scroll(-1)
            return
        if getattr(event, "ctrl", False):
            self._zoom_map(1)
            return
        if not self.home_mode and self.panel_mode == "pause":
            # 暂停菜单：滚轮在选项间挪光标（PauseListView 已接，这里兜住
            # 落在标题/键位提示/边距上的滚轮）。
            self.pause_move(-1)
            return
        if self.panel_mode == "event_dialog":
            # 复合事件对话：滚轮滚动上方文字（选项固定在底部不随动）。
            self.event_dialog_scroll = max(0, self.event_dialog_scroll + -1 * 2)
            self.refresh_view()
            return
        if self.insight_replace_target is not None:
            # 替换面板：滚轮在现有洞察之间移动光标（列表可能比面板长）。
            self.move_insight_replace_cursor(-1)
            return
        if self.memory_replace_target is not None:
            # 碎片替换面板：滚轮在现有碎片之间移动光标。
            self.move_memory_replace_cursor(-1)
            return
        if self.anomaly_detail_target is not None or self.cell_detail_target is not None:
            self._scroll_anomaly_detail(1)
            return
        if self.panel_mode == "equipment" and self._memory_region_row_at(event):
            # 悬停在底部记忆碎片区上：滚轮只滚碎片区，不滚上方装备列表（2026-10-14）。
            self._scroll_memory(-1)
            return
        self._scroll(1)

    def on_mouse_scroll_down(self, event: MouseScrollDown) -> None:
        self._note_activity()
        if self._scroll_right_panel(event, -1):
            return
        if self._inspection_active():
            event.stop()
            return
        if self._layer_scroll(event, 1):
            return
        if self._active_tamper_editor() is not None:
            event.stop()
            return
        if self._scroll_self_audit(event, 1):
            return
        if self._scroll_layer_info(event, 1):
            return
        if getattr(self, 'controls_help_open', False):
            event.stop()
            return
        if self.panel_mode == 'home_newgame':
            self.query_one('#newgame-scroll').scroll_relative(y=3, animate=False)
            return
        if not self.home_mode and self.panel_mode == "board_editor":
            self.board_editor_scroll(1)
            return
        if getattr(event, "ctrl", False):
            self._zoom_map(-1)
            return
        if not self.home_mode and self.panel_mode == "pause":
            self.pause_move(1)
            return
        if self.panel_mode == "event_dialog":
            # 复合事件对话：滚轮滚动上方文字（选项固定在底部不随动）。
            self.event_dialog_scroll = max(0, self.event_dialog_scroll + 1 * 2)
            self.refresh_view()
            return
        if self.insight_replace_target is not None:
            self.move_insight_replace_cursor(1)
            return
        if self.memory_replace_target is not None:
            self.move_memory_replace_cursor(1)
            return
        if self.anomaly_detail_target is not None or self.cell_detail_target is not None:
            self._scroll_anomaly_detail(-1)
            return
        if self.panel_mode == "equipment" and self._memory_region_row_at(event):
            self._scroll_memory(1)
            return
        self._scroll(-1)
