"""键位路由族：on_key 主路由、观察/锁定/面板键处理与 escape 链。"""
from __future__ import annotations

import time

from textual.events import MouseDown, MouseMove, MouseScrollDown, MouseScrollUp
from textual.widgets import Input, Static

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

class KeyRoutingMixin:
    """键位路由族：on_key 主路由、观察/锁定/面板键处理与 escape 链。"""

    # on_key 与底栏绑定共用同一个按键的键名归一：Enter 在 Textual 里既可能是
    # "enter" 也可能是 "return"，底栏键位只认 "enter"。
    _BINDING_KEY_ALIASES = {"return": "enter"}
    def _mark_key_handled(self, key: str) -> None:
        """记下「这个键已经由 on_key 处理过」。

        Textual 的派发顺序是 on_key 先于非 priority 绑定动作，所以同一个键在
        on_key 里结算一次之后，底栏绑定还会被触发第二次。标记之后，绑定入口
        （action_act_action / action_descend_action / action_backtrack_action）
        会用 :meth:`_handled_in_on_key` 把那次重复触发吃掉。
        非底栏键位随手标记也无害：每次按键都会清空这个集合。
        """
        self._keys_handled_in_on_key.add(self._BINDING_KEY_ALIASES.get(key, key))

    def _handled_in_on_key(self, key: str) -> bool:
        """底栏绑定入口：这次触发是否紧跟在该键的 on_key 处理之后（是则空转）。"""
        if key in self._keys_handled_in_on_key:
            self._keys_handled_in_on_key.discard(key)
            return True
        return False
    # ---- 观察模式 ----
    # 定位与鼠标悬停一致（同一个读数、同一套可见性规则），区别只是由键盘驱动：
    # 自己留在原地不动，一枚白色 ? 代替「可操作对象」在地图上移动——它可以穿过
    # 墙体与生物（只是到不了意识边界之外），而一切输入都不消耗回合、时间静止、
    # 视野也不重算。视野外的东西同样看不全（与悬停一致）。

    def toggle_observe(self) -> None:
        """进入 / 退出观察模式（x 键或底栏「观察」，Enter/Q/Esc 也可退出）。"""
        self._panel_enter_mode = None
        self.assist_path = []
        self.observe_walk_path = []
        if self.observe_mode:
            self.exit_observe()
            self.refresh_view()
            return
        state = self.session.state
        self.observe_mode = True
        self.observe_cursor = (state.player.x, state.player.y)
        # 悬停读数跟着 ? 走：右上角显示「观察:」与该格坐标/地形。
        self.hover_cell = self.observe_cursor
        self.path.clear()
        self.observe_walk_path.clear()
        self.pickup_goal = None
        self._clear_held()
        self.refresh_view()

    def exit_observe(self) -> None:
        """退出观察模式（可反复调用）：操作对象重新回到自己身上。"""
        self.observe_mode = False
        self.observe_cursor = None
        self.hover_cell = None
        self.path.clear()
        self.observe_walk_path.clear()
        self.pickup_goal = None

    def _observe_bounds(self, x: int, y: int) -> tuple[int, int]:
        """把观察光标的坐标钳在意识边界之内（内圈 1..边长-2）。

        ? 能穿过墙体与生物，但走不出边界——「只能到达，不能穿过边界外面」。
        """
        state = self.session.state
        return (
            min(max(1, x), max(1, state.width - 2)),
            min(max(1, y), max(1, state.height - 2)),
        )

    def _move_observe_cursor(self, dx: int, dy: int) -> None:
        """观察模式的方向键：? 走一格（无视墙与生物），不推进时间。"""
        state = self.session.state
        cx, cy = self.observe_cursor or (state.player.x, state.player.y)
        self.path.clear()
        self.observe_walk_path.clear()
        self.observe_cursor = self._observe_bounds(cx + dx, cy + dy)
        self.hover_cell = self.observe_cursor
        if self.target_assist:
            # 双模式：? 每动一格，显示路径刷新为「玩家 → ?」的玩家寻路。
            self._refresh_assist_path(self.observe_cursor)
        self._refresh_cursor_only()

    def _refresh_cursor_only(self) -> None:
        if not self.is_mounted:
            return
        map_view = self.query_one("#map", MapView)
        map_view.observe_cursor = (self.sentence_aim['cursor'] if self.sentence_aim is not None
                                   else getattr(self, '_aim_free_cursor', None) if self.aiming
                                   else self.observe_cursor if self.observe_mode else None)
        map_view.assist_cells = set(self.assist_path) if self.target_assist or self.aiming else None
        if self.layer_observation is not None:
            map_view.observe_cursor = self.layer_observation.cursor
        map_view.update_interaction()
        self.refresh_hover_only()
        self._refresh_signal_status()
    def _observe_walk_to(self, target: tuple[int, int]) -> None:
        """观察模式的点击寻路：无视障碍，直接走最短格子。

        与世界的 8 向 A* 不同，这里不查墙体与生物——? 是目光而不是身体，
        所以最短的「楼梯形」折线就是它的路径；终点同样钳在内圈。
        """
        state = self.session.state
        tx, ty = self._observe_bounds(*target)
        cx, cy = self.observe_cursor or (state.player.x, state.player.y)
        path: list[tuple[int, int]] = []
        x, y = cx, cy
        # 8 向步行：两轴同时推进时走对角格，观感为一条斜线直达。
        while (x, y) != (tx, ty):
            if x != tx:
                x += 1 if tx > x else -1
            if y != ty:
                y += 1 if ty > y else -1
            path.append((x, y))
        self.observe_walk_path = path
        self.hover_cell = self._observe_bounds(tx, ty)
        self._refresh_cursor_only()

    def _handle_observe_key(self, key: str, character: str | None) -> None:
        """观察模式下的按键：只挪 ? 或退出，绝不落地任何世界行动。

        三条硬约束：时间不动（没有任何 ``session.apply``）、视野不重算、
        自己不挪步。能做的只有「挪 ?」「切界面」「退出观察」。

        ``x``/``q``/``Esc``/``Enter`` 都是「结束观察」——行动键在此没有可做的
        行动，但也不能毫无反馈。这几个键同时标记为「已在 on_key 处理」，否则
        紧跟其后的底栏绑定（x 观察 / Esc 保存并退出 / Enter 行动）会把刚退出的
        观察模式再翻回来、或直接存档退出。
        """
        if key in ("enter", "return"):
            self._mark_key_handled("enter")
            state = self.session.state
            cursor = self.observe_cursor or (state.player.x, state.player.y)
            walk = state.path_to(*cursor)
            if walk or cursor == (state.player.x, state.player.y):
                self.toggle_observe()
                self.path = list(walk)
                self.assist_path = []
                self._refresh_cursor_only()
            else:
                self._cancel_unreachable_path()
                self._refresh_cursor_only()
            return
        if key in ("x", "q", "escape", "enter", "return"):
            self._mark_key_handled(key)
            self.toggle_observe()
            return
        direction = self._direction_map().get(key)
        if direction is not None:
            self._move_observe_cursor(*direction)
            return
        # Alt+方向 = 地图缩放（原 Ctrl+方向迁移；Ctrl 序列保留兼容）。
        if key in ("ctrl+up", "ctrl+down", "alt+up", "alt+down"):
            self._zoom_map(1 if key in ("ctrl+up", "alt+up") else -1)
            return
        panel = self._panel_shortcut_for(key, character)
        if panel is not None:
            # 界面键照常可用：面板切换不改变世界状态，也不推进时间。
            self.path.clear()
            self.observe_walk_path.clear()
            self._toggle_panel(panel)
            return
        # 其余按键与世界的「任意按键刹停寻路」一致：刹停 ? 的寻路，别的什么都不做。
        self.path.clear()
        self.observe_walk_path.clear()
        self._refresh_cursor_only()

    def _follow_observe_path(self) -> None:
        """观察模式下由寻路节拍推进 ?（每个节拍一格）。

        与世界的 ``_follow_path`` 不同：这里既不查生物也不推时间，? 是目光，
        沿线每一格都只是「换个落点」，所以直接弹出一格坐标即可。
        """
        if not self.observe_walk_path:
            return
        self.observe_cursor = self._observe_bounds(*self.observe_walk_path.pop(0))
        self.hover_cell = self.observe_cursor
        if self.target_assist:
            self._refresh_assist_path(self.observe_cursor)
        self._refresh_cursor_only()

    def _clear_held(self) -> None:
        """清除按住状态（松开/切换界面/被阻挡时）。"""
        self._held_key = None
        self._held_direction = None
        self._hold_repeats = 0
    # 面板光标移动键（三套键位共用一套映射）：
    #   - 竖轴：↑↓ 上下移动选中/滚动；
    #   - 横轴：←→ 在界面之间切页。
    #
    # 🔴 键位分工（2026-09-16 第三次定稿，玩家拍板「上下左右和 WASD 功能互换」）：
    #   · **方向键（上下左右）→ 地图移动**（无论锁定与否——锁定时按下面板分支）。
    #     原因：NumLock 关闭时 Windows 把小键盘 2/4/6/8 直接当成方向键发送
    #     （终端字节层面与真方向键完全相同、无法区分），方向键归移动，
    #     小键盘 2468 才能随时走地图；1/3/7/9（Home/End/PgUp/PgDn）本来就
    #     落到移动分支出斜向，NumLock 开关都能用。
    #   · **WASD → 面板选取**（「随时」：解锁也动面板，锁定同样动面板）。
    #   · 小键盘数字（NumLock 开时是数字字符）→ 地图移动。
    #   · 锁定（~ / `）后三套全部只动面板。
    #
    # ⚠️ 小键盘的真实键名（2026-09-16 实测，别照着手册猜）：
    #   Textual 的按键表里**根本没有** num8/kp8 这类名字（已核对
    #   textual/_ansi_sequences.py）。真实终端行为：
    #     · NumLock **开**  → 小键盘发来普通字符 "8"/"2"/"4"/"6"（对角 "7"/"9"/"1"/"3"）；
    #     · NumLock **关**  → 2468 发来与方向键**完全相同**的 VT 序列（up/down/left/right，
    #       终端层面无法区分）；7/1/9/3 发来 home/end/pageup/pagedown（不在
    #       面板键表里，自然落到移动分支出斜向——所以 NumLock 关也能斜走）。
    #   另有原生 Windows 驱动的坑见 windows_mouse.py::classify_key_batch
    #   （SS3 序列曾被误判成 Alt 整批吞掉，cef2489 修复）。
    LOCKED_MOVE_KEYS = {
        "up": ("v", -1), "down": ("v", 1), "w": ("v", -1), "s": ("v", 1),
        "8": ("v", -1), "2": ("v", 1), "num8": ("v", -1), "num2": ("v", 1),
        "kp8": ("v", -1), "kp2": ("v", 1),
        "left": ("h", -1), "right": ("h", 1), "a": ("h", -1), "d": ("h", 1),
        "4": ("h", -1), "6": ("h", 1), "num4": ("h", -1), "num6": ("h", 1),
        "kp4": ("h", -1), "kp6": ("h", 1),
        # 小键盘对角键（7/9/1/3）：面板里没有对角位移，只用于「上下滚动」——
        # 与主键盘 PgUp/PgDn 同义（见类注释：它们不在本表时自然落到移动分支）。
        "7": ("v", -1), "9": ("v", -1), "1": ("v", 1), "3": ("v", 1),
        "num7": ("v", -1), "num9": ("v", -1), "num1": ("v", 1), "num3": ("v", 1),
        "kp7": ("v", -1), "kp9": ("v", -1), "kp1": ("v", 1), "kp3": ("v", 1),
    }

    # 「面板键」子集：即使没开锁定，它们也移动面板光标（2026-09-16 玩家拍板：
    # WASD 与方向键互换——WASD 随时管面板选取，方向键随时管地图移动）。
    # 注意只放 WASD 这四个**主键位**；方向键绝不能进来（否则 NumLock 关时
    # 小键盘 2468 又会被面板占走，回到玩家投诉的状态）。
    WASD_PANEL_KEYS = frozenset({"w", "a", "s", "d"})

    # 左侧覆盖面板：打开时**默认锁定**（三套键位都动光标），且只能「先退出、
    # 再行动」——第一下按键/左键地图只关面板，第二下才落到游戏上。
    LEFT_OVERLAY_ATTRS = (
        "item_menu_target", "anomaly_detail_target", "cell_detail_target",
        "insight_replace_target", "memory_replace_target", "pickup_target",
    )

    # ⚠️ 不可被打断的左侧面板：只能靠面板自己的「选中确认」退出，
    # 其他键与点击一律被吞掉（不关面板、不行动）。替换洞察/替换记忆属此列。
    NON_INTERRUPTIBLE_OVERLAY_ATTRS = ("insight_replace_target", "memory_replace_target")

    # 物品菜单自己的功能键（U 携带/卸下/使用、D 放下、Q 投掷）。
    # 它们是**面板自己的选中确认**，按下即执行——等同于左键点那行按钮。
    # 与「左侧面板默认锁定、先退出再行动」不冲突：那条规则管的是**面板之外的
    # 按键**（WASD/小键盘/E/N 之类），它们才会被面板吃掉、只关面板不动世界。
    MENU_ACTION_KEYS = ("u", "d")

    def _move_menu_cursor(self, key: str) -> bool:
        """物品菜单光标：↑↓ 在功能行之间移动（用于悬停高亮），←→ 与其他键不处理。

        返回 True 表示按键已被菜单消费。
        """
        move = self.LOCKED_MOVE_KEYS.get(key)
        if move is None:
            return False
        axis, delta = move
        rows = [index for index, value in enumerate(self._menu_rows) if isinstance(value, str)]
        if not rows:
            return True
        current = self._menu_hover_row
        if current is None or current not in rows:
            order = 0 if delta < 0 else 0
            self._menu_hover_row = rows[order]
        else:
            order = max(0, min(len(rows) - 1, rows.index(current) + delta))
            self._menu_hover_row = rows[order]
        self.refresh_view()
        return True

    def _active_left_overlay(self) -> str | None:
        """当前打开的左侧覆盖面板的属性名（同时最多一个；都没有则 None）。"""
        return next((name for name in self.LEFT_OVERLAY_ATTRS if getattr(self, name, None) is not None), None)

    def _left_overlay_blocks_interrupt(self) -> bool:
        """打开的左侧面板是否「不可被打断」（替换洞察/替换记忆）。"""
        active = self._active_left_overlay()
        return active is not None and active in self.NON_INTERRUPTIBLE_OVERLAY_ATTRS

    def _close_active_left_overlay(self) -> bool:
        """关掉当前左侧覆盖面板；返回是否确实关掉了一个。"""
        active = self._active_left_overlay()
        if active is None:
            return False
        # 浮层没了，/ 键切出来的 overlay 焦点失效：归位地图，别留悬空状态。
        if getattr(self, "cursor_zone", "map") == "overlay":
            self.cursor_zone = "map"
        {
            "item_menu_target": self.close_item_menu,
            "anomaly_detail_target": self.close_anomaly_detail,
            "cell_detail_target": self.close_cell_detail,
            "pickup_target": self.close_pickup,
            # 替换类面板不在这里关：它们走自己的「放弃确认」流程。
        }.get(active, lambda: None)()
        return True

    def _should_move_map_with_keys(self) -> bool:
        """没开锁定时方向键/小键盘是否应该直接移动地图。

        右侧面板（事件记录/行囊/携带意象/征兆/洞察/观测/操作）不再隐式锁键：
        玩家可以从这些界面直接用方向键/小键盘走过去（2026-09-16 互换后 WASD
        随时管面板选取，方向键管移动）。感知类面板（征兆/观测）会在移动时
        自动回到事件记录——它们没有选中项，留在原地也没有意义。
        """
        if self.panel_locked or self.observe_mode or self.home_mode:
            return False
        if self._active_left_overlay() is not None:
            return False
        return True

    def _prepare_map_move_from_panel(self) -> None:
        """从右侧面板发起地图移动前的界面切换。

        2026-09-19 修订：征兆/观测/构想页获得真实选中项后，方向键移动不再
        把界面拉回事件记录——保留原界面，选中状态原样保留。
        """
        self._panel_enter_mode = None
        if self.panel_mode in ("catalog",):
            self.panel_mode = "world"
            self.panel_selection = 0
            self.panel_scroll = 0

    def toggle_cursor_lock(self) -> None:
        """切换面板光标锁定（键盘反引号 / 波浪号，或底栏「锁定」按钮）。

        这两个键由 :meth:`on_key` 归一成同一个键，见那里的注释。
        """
        if self.panel_locked:
            self.release_cursor_lock()
            return
        self.panel_locked = True
        self.refresh_view()

    def release_cursor_lock(self) -> None:
        """解锁面板光标——**解锁的唯一出口**，三条通道（~ / ` 切换、Esc、点击地图）都走这里。

        锁定时 ←→ 会在「世界 → 六个界面」之间来回切页，解锁时面板可能正停在
        背包/携带意象/观测之类的界面上，玩家解锁后既看不见事件记录、也容易以为界面坏了。
        因此解锁一律把面板切回事件记录界面（world），方便立刻继续移动。
        主页模式没有面板可锁，保持原样。
        """
        self.panel_locked = False
        if not self.home_mode:
            self.panel_mode = "world"
            self.panel_selection = 0
        self.refresh_view()
    # 光标焦点区域（/ 键，2026-10-12）：同屏键盘焦点在「地图 ↔ 右侧面板 ↔
    # 左侧浮层」之间强制切换。锁定态（~）仍旧全局生效——它本来就是「全部
    # 归面板」，zone 只在解锁态给方向键一个明确的去处。
    CURSOR_ZONE_LABELS = {
        "map": "光标区域：地图（方向键移动，WASD 动面板）",
        "panel": "光标区域：右侧面板（方向键/WASD 都动面板，←→ 切页）",
        "overlay": "光标区域：左侧浮层",
    }

    def cycle_cursor_zone(self) -> None:
        """在「地图 → 右侧面板 →（浮层，若开着）」之间循环切换键盘焦点区域。

        切换本身只改 zone 状态与提示；方向键的去向由 on_key 的分流读取
        （zone == "panel" 时方向键与 WASD 一样只动面板光标）。浮层关闭后
        overlay 不再是合法区域，循环时自动归位 map。
        """
        if self.home_mode:
            return
        zones = ["map", "panel"]
        if self._active_left_overlay() is not None:
            zones.append("overlay")
        current = getattr(self, "cursor_zone", "map")
        if current not in zones:
            current = "map"
        self.cursor_zone = zones[(zones.index(current) + 1) % len(zones)]
        self._panel_enter_mode = None
        self.show_toast(tr(self.CURSOR_ZONE_LABELS[self.cursor_zone]))
        self.refresh_view()

    def _locked_panel_key(self, key: str) -> bool:
        """方向系按键的面板处理：只移动面板光标/滚动，不动游戏。

        世界面板（事件记录）没有可选中条目，它的 ↑↓ 就是「回看历史」——
        **锁定与否都生效**（2026-09-16 玩家要求：解锁状态也该能翻事件记录）。
        注意它只在**当前就在 world 界面**时滚动；其它界面上的 ↑↓ 照旧移动
        该界面的选中项，不会顺手把事件记录滚掉。
        """
        move = self.LOCKED_MOVE_KEYS.get(key)
        if move is None:
            return False
        axis, delta = move
        if axis == "h":
            if self.panel_mode == 'inventory':
                self.cycle_panel_subpage(delta)
                return True
            from ..sidebar_workspaces import ROUTES
            routes = [route for route in ROUTES.get(self.sidebar_workspace, ()) if not route.mode.startswith('@')]
            index = next((i for i, route in enumerate(routes)
                          if route.mode == self.panel_mode and (not route.subpage or route.subpage == self._panel_subpage_id())), None)
            if index is not None:
                target = max(0, min(len(routes) - 1, index + delta))
                self.open_sidebar_route(routes[target].key)
            return True
        if self.panel_mode == 'journal_log':
            self._scroll(-delta)
            return True
        self._move_panel_selection(delta)
        return True


    def _handle_locked_keys(self, key: str, character) -> bool:
        """锁定态按键总入口：返回 True 表示按键已被锁定层消费。

        （` / ~ 的锁定与解锁由 on_key 归一处理、底栏按钮走同一条 action，
        不经过这里——两处都切会互相抵消。）
        """
        if key in ("escape",):
            # Esc 在锁定态只解锁（吃掉保存退出那次绑定触发）。
            self._mark_key_handled("escape")
            self.release_cursor_lock()
            return True
        return self._locked_panel_key(key)

    def _open_container_overlay(self, index: int) -> None:
        """打开容器 overlay（左侧浮层）：盛装/倒出完成后留在行囊界面。"""
        self.container_index = index
        # 容器浮层独占左侧：关掉其它左侧浮层，避免渲染链打架。
        self.item_menu_target = None
        self.anomaly_detail_target = None
        self.close_cell_detail()
        self.path.clear()
        if self.panel_mode != "inventory":
            self.panel_mode = "inventory"
        self.event_dialog_scroll = 0
        self.refresh_view()
    def _handle_action_key(self) -> None:
        """「行动」键的统一实现：键盘 Enter 与底栏「Enter 行动」按钮共用这一条路径。

        世界里它是「只做相邻事务」的行动：回应相邻的未解异常地点、取走相邻台子
        （木桌子/石台）台面上的显化物——脚下的显化物与地点的回应都不归它
        （拾取是 G，踩上去自动拾取）。其余上下文中沿用 Enter 原有的语义——主页
        载入存档、确认攻击、面板条目激活。世界里相邻无事可做、且已达成醒来条件时，
        这次按键才退化为「结束入梦」。
        """
        if self.observe_mode:
            self._handle_observe_key("enter", None)
            return
        if self.item_menu_target is not None:
            self.close_item_menu()
            return
        if self.anomaly_detail_target is not None:
            self.close_anomaly_detail()
            return
        if self.cell_detail_target is not None:
            self.close_cell_detail()
            return
        if self.home_mode:
            # 2026-09-18 恢复：主页 Enter = 激活光标项（与左键同路）。
            # 「删除」的两段确认逻辑在 activate_home_selection 内部。
            # 图鉴/设置页里的 Enter 仍是它们各自的「进入条目 / 修改设置」。
            if self.panel_mode == "home_catalog":
                self._handle_codex_key("enter")
            elif self.panel_mode == "home_settings":
                self._handle_settings_key("enter", None)
            self.activate_home_selection()
            return
        if self.pending_confirmation:
            _, target = self.pending_confirmation
            self._execute_confirmed_attack(target)
            return
        if self.path:
            # 与「寻路中任意按键先刹停」一致：只停止，不额外行动。
            self.path.clear()
            self.observe_walk_path.clear()
            self.pickup_goal = None
            self.refresh_view()
            return
        panel_intent = (self.panel_locked or self.cursor_zone == 'panel'
                        or getattr(self, '_panel_enter_mode', None) == self.panel_mode)
        explicit_modes = ('world', 'inventory', 'equipment', 'build_overview', 'self_overview', 'self_stats', 'nearby', 'sidebar_detail')
        if (self.panel_mode not in explicit_modes or panel_intent):
            self._activate_panel_selection()
            return
        if not self._act_on_player_cell():
            state = self.session.state
            # 脚下无事可做、且已达成醒来条件：这次「行动」改为结束入梦。
            if state.victory and not state.run_over and self._apply("finish_run").changed:
                self.exit()
                return
        self.refresh_view()

    def _actions_for(self, target: tuple[int, int]) -> list[str]:
        state = self.session.state
        actions: list[str] = []
        if not (0 <= target[0] < state.width and 0 <= target[1] < state.height):
            # 换层残留的旧坐标：本层没有这个格子，只剩观察。
            return ["观察"]
        entity = state.entity_at(*target)
        adjacent = max(abs(target[0] - state.player.x), abs(target[1] - state.player.y)) <= 1
        if entity and entity is not state.player and adjacent:
            actions.append("攻击" if entity.relation == "失控意识" else ("交谈" if entity.relation == "稳定意识" else "攻击（需确认）"))
        if any((entry.x, entry.y) == target for entry in state.world_items) and target == (state.player.x, state.player.y):
            actions.append("拾取")
        if any(not event.resolved and (event.x, event.y) == target for event in state.events) and adjacent:
            actions.append("回应")
        if adjacent and state.is_visible(*target) and state.cell(*target).light_radius>0:
            # §12 F：弧光灯架（跟电路）与余烬灯盏（跟火焰）没有开关可拨，
            # 不给「熄灭光源」这一项，免得玩家以为能直接关灯。
            from ...materials import FLAME_FIXTURE_KINDS, POWERED_FIXTURE_KINDS
            switchable = state.cell(*target).wall_kind not in (
                FLAME_FIXTURE_KINDS | POWERED_FIXTURE_KINDS)
            if switchable:
                actions.append('熄灭光源' if state.cell(*target).light_on else '点亮光源')
        if adjacent and state.is_visible(*target):
            from ...core.tactical_layouts import gate_control_at
            record=gate_control_at(state,*target)
            if record is not None and not record.flags.get('resolved'):
                actions.append('拨开门纹')
        if not actions and adjacent and not state.cell(*target).solid:
            actions.append("移动")
        if not actions and adjacent and state.cell(*target).solid:
            actions.append("打开")
        if state.realm_id == "toy_memories":
            actions.append("重置本层机关")
        return actions or ["观察"]
    def _panel_item_count(self) -> int:
        state = self.session.state
        if self.panel_mode == "inventory":
            return len(state.inventory)
        if self.panel_mode == "equipment":
            # 记忆碎片是独立分层页：整页只读，没有可选条目。
            if self._panel_subpage_id() == "memory":
                return 0
            return sum(1 for item in state.inventory if item.slot)
        if self.panel_mode == "portents":
            return len(PORTENT_DEFINITIONS)
        if self.panel_mode == "insights":
            return len(state.insights)
        if self.panel_mode == "catalog":
            return len(self.session.state.visible_anomalies())
        if self.panel_mode == "actions":
            page = self._panel_subpage_id()
            if page == "fire":
                return 0
            if page == "tamper":
                return 1
            context = len(self._actions_for(self.context_menu_target)) if self.context_menu_target else 0
            return (context + len([a for a in state.abilities if a in ABILITY_DEFINITIONS])
                    + len(state.identity_abilities()) + len(state.equipment.active_sentence_options()))
        return 0
    def _move_panel_selection(self, delta: int) -> None:
        # WASD selects the panel without changing the direction keys' map focus.
        self._panel_enter_mode = self.panel_mode
        if self.panel_mode == "equipment":
            self._move_equipment_selection(delta)
            return
        count = self._panel_item_count()
        if count:
            self.panel_selection = (self.panel_selection + delta) % count
        if self.panel_mode == "portents":
            self._follow_portent_selection()
        elif self.panel_mode in ("inventory", "insights"):
            self._follow_list_selection()
        elif self.panel_mode == "actions":
            self._follow_actions_selection()
        self.refresh_view()
    def _move_equipment_selection(self, delta: int) -> None:
        """装备盘页移动选中；记忆碎片分层页 ↑↓ 滚该页（整页只读）。"""
        if self._panel_subpage_id() == "memory":
            total = len(self.session.state.memory_fragments) + 3
            viewport = max(1, self._portent_viewport_rows() - 1)
            self.panel_scroll = max(0, min(max(0, total - viewport),
                                          self.panel_scroll + delta))
            self.refresh_view()
            return
        count = self._panel_item_count()
        if count:
            self.panel_selection = (self.panel_selection + delta) % count
            self._follow_list_selection()
        self.refresh_view()
    def _scroll_memory(self, delta: int) -> None:
        """滚动底部记忆碎片独立滚动区（delta>0 向下看更后面的碎片）。"""
        total = len(self.session.state.memory_fragments)
        max_scroll = max(0, total - MEMORY_FOOTER_ITEM_ROWS)
        self.memory_scroll = min(max_scroll, max(0, self.memory_scroll + delta))
        self.refresh_view()

    def _memory_region_row_at(self, event) -> bool:
        """滚轮悬停判定：鼠标当前落在记忆碎片区行（row_index == -2）上。"""
        widget = getattr(event, "control", None)
        if getattr(widget, "id", None) != "panel":
            return False
        rows = self._panel_rows
        if not rows:
            return False
        try:
            y = event.offset.y + int(widget.scroll_offset.y)
        except Exception:
            y = event.offset.y
        return 0 <= y < len(rows) and rows[y] == -2

    def _follow_actions_selection(self) -> None:
        """键盘移动选择时把操作界面的条目滚进视窗（2026-09-21）。

        与 `_follow_list_selection` 同一手感：操作界面改成首行偏移切片后，
        键盘选中的条目（构想/目标操作）必须跟着滚进来，否则 ▶ 停在
        视窗外、按 Enter 像是「没反应」。
        """
        lines, row_indices = self._actions_lines(self.session.state)
        if not lines:
            return
        starts = [i for i, row in enumerate(row_indices) if row == self.panel_selection]
        if not starts:
            return
        top = starts[0]
        bottom = starts[-1] + 1
        viewport = self._portent_viewport_rows()
        strip_lines = self._panel_subtabs_lines()
        if strip_lines:
            viewport = max(1, viewport - len(strip_lines))
        if top < self.panel_scroll:
            self.panel_scroll = top
        elif bottom > self.panel_scroll + viewport:
            self.panel_scroll = max(0, bottom - viewport)

    def _follow_list_selection(self) -> None:
        """键盘移动选择时把这个条目滚进视窗（行囊/携带意象/洞察与征兆同一手感）。

        每个条目可能占多行（注释展开时），所以定位要用「该条目在行列表里的
        起始行/结束行」而不是「条目序号 == 行号」。
        """
        lines, row_indices, _header = self._panel_lines(self.session.state)
        if not lines:
            return
        if self.panel_mode == "equipment":
            equipment_indices = [i for i, item in enumerate(self.session.state.inventory) if item.slot]
            if equipment_indices and self.panel_selection < len(equipment_indices):
                real_index = equipment_indices[self.panel_selection]
            else:
                return
        else:
            real_index = self.panel_selection
        starts = [i for i, row in enumerate(row_indices) if row == real_index]
        if not starts:
            return
        top = starts[0]
        bottom = starts[-1] + 1
        viewport = self._portent_viewport_rows()
        strip_lines = self._panel_subtabs_lines()
        if strip_lines:
            viewport = max(1, viewport - len(strip_lines))
        if self._panel_footer(self.session.state) is not None:
            viewport = max(1, viewport - 1)
        if top < self.panel_scroll:
            self.panel_scroll = top
        elif bottom > self.panel_scroll + viewport:
            self.panel_scroll = max(0, bottom - viewport)

    def _follow_portent_selection(self) -> None:
        """键盘移动选择时把该条征兆滚进视窗，实现「键盘滑动」。"""
        _lines, starts, total = self._portent_layout(self.session.state)
        if not starts:
            return
        index = min(max(self.panel_selection, 0), len(starts) - 1)
        viewport = self._portent_viewport_rows()
        top = starts[index]
        bottom = starts[index + 1] if index + 1 < len(starts) else total
        if top < self.panel_scroll:
            self.panel_scroll = top
        elif bottom > self.panel_scroll + viewport:
            self.panel_scroll = max(0, bottom - viewport)

    def _move_panel_tab(self, delta: int) -> None:
        """Cycle workspaces; business shortcuts keep their original targets."""
        from ..sidebar_workspaces import WORKSPACES
        modes = [row[0] for row in WORKSPACES]
        if self.sidebar_workspace not in modes:
            return
        index = max(0, min(len(modes) - 1, modes.index(self.sidebar_workspace) + delta))
        if self.open_sidebar_workspace(modes[index]):
            self._panel_enter_mode = self.panel_mode

    def _activate_panel_selection(self, key_hint: str | None = None) -> None:
        """激活面板当前选中条目（Enter 与左键共用）。

        ``key_hint`` 是点击时从渲染快照取到的条目键（见 ``_panel_row_keys``）。
        键盘路径不传，退回按 ``panel_selection`` 现算——两条路径都能定位，
        且点击路径不受「渲染后目标操作条数变化」的影响。
        """
        state = self.session.state
        if self.panel_mode == "equipment" and self._panel_subpage_id() == "memory":
            # 记忆碎片分层页整页只读：Enter 不触发装备/拾取。
            return
        if self.panel_mode in ("inventory", "equipment") and state.inventory:
            if self.panel_mode == "equipment":
                # panel_selection 是「行囊中的携带意象」列表里的位置，换算回真实下标。
                equipment_indices = [index for index, item in enumerate(state.inventory) if item.slot]
                if equipment_indices:
                    index = equipment_indices[min(self.panel_selection, len(equipment_indices) - 1)]
                    self.open_board_editor_for_item(index)
            else:
                index = min(self.panel_selection, len(state.inventory) - 1)
                item = state.inventory[index]
                result = None
                if item.effect == "container":
                    # 容器：打开左侧盛装/倒出浮层（不耗时）；关闭后留在行囊。
                    result = self._apply("use", index)
                    if result.data.get("container_menu") is not None:
                        self._open_container_overlay(result.data["container_menu"])
                    else:
                        self.refresh_view()
                elif item.category in ("摄入物", "易逝物", "交互道具", "惯用物"):
                    result = self._apply("use", index)
                    self.show_toast(result.message, self._selected_panel_row_screen_y())
                elif item.slot:
                    # 携带意象：不再静默穿上/脱下——改为带着它进联想盘编辑器（§8.4）。
                    # 记忆槽不上盘，走旧的穿/脱入口。
                    if not self.open_board_editor_for_item(index):
                        result = self._apply("toggle_equip", index)
                        self.show_toast(result.message, self._selected_panel_row_screen_y())
        elif self.panel_mode == "insights":
            if key_hint is None and state.insights:
                key_hint = state.insights[min(self.panel_selection, len(state.insights) - 1)]
            if key_hint == "蜂鸣回响":
                # §11 §7：广播加成可在详情关闭；切换本身不发声、不耗时。
                state.buzzing_echo_enabled = not getattr(state, "buzzing_echo_enabled", True)
                self.expanded_key = key_hint
                self.show_toast(tr("蜂鸣回响：广播加成已开启。") if state.buzzing_echo_enabled
                                else tr("蜂鸣回响：广播加成已关闭。"),
                                self._selected_panel_row_screen_y())
            elif key_hint:
                # 键盘与左键等价：Enter 展开／收起该洞察的说明。
                self.expanded_key = None if self.expanded_key == key_hint else key_hint
        elif self.panel_mode == "actions":
            page = self._panel_subpage_id()
            if page == "fire":
                self.show_toast(tr("发射页只读：按 F 进入发射瞄准。"), self._selected_panel_row_screen_y())
                return
            if page == "tamper":
                if self.open_world_tamper_editor():
                    self.refresh_view()
                return
            # 定位口径统一走**条目键**（"ability:xxx" / "action:n"），不再按
            # 「目标操作条数」做下标算术——那个数字在渲染与点击之间会变。
            if key_hint is None:
                key_hint = self._panel_entry_key(self.panel_selection)
            if key_hint is None:
                # 这一行已经没有可执行的条目（例如目标格变化后条目对不上）。
                # 用户要求：条件触发不了也必须给左侧气泡，绝不静默无反应。
                self.show_toast(tr("这一行现在没有可执行的操作。"),
                                self._selected_panel_row_screen_y())
                self.refresh_view()
                return
            if key_hint.startswith('sentence:'):
                self._begin_sentence_aim(key_hint.split(':', 1)[1])
                return
            if key_hint.startswith('identity:'):
                ability = key_hint.split(':', 1)[1]
                target = self.context_menu_target
                args = (ability, *target) if ability == 'retract' and target else (ability,)
                result = self._apply('identity_ability', *args)
                self.show_toast(result.message, self._selected_panel_row_screen_y())
                self.refresh_view()
                return
            if key_hint.startswith("ability:"):
                ability_id = key_hint.split(":", 1)[1]
                if ability_id not in ABILITY_DEFINITIONS:
                    self.show_toast(tr("未知的构想。"), self._selected_panel_row_screen_y())
                    self.refresh_view()
                    return
                # §13/§12 H2：战斗与选点构想先进入零消耗瞄准，真正支付在确认时发生。
                from ...core.combat_constructs import is_combat
                from ...core.ability_targeting import is_targeted
                if is_combat(ability_id) or is_targeted(ability_id):
                    if not self.begin_construct_aim(ability_id):
                        self.show_toast(tr("这个构想现在无法瞄准。"),
                                        self._selected_panel_row_screen_y())
                        self.refresh_view()
                    return
                # [SFX挂点] 使用主动构想：展开成功播 construct（先声后动也自然）。
                ability_result = self.session.state.activate_ability(ability_id)
                if ability_result.changed:
                    from ...core.origin_course import note
                    note(self.session.state,'ability_cast')
                    # §15.6：结算完成即撤掉预览标记，不留上一发的作用区。
                    self._invalidate_terrain_preview()
                # 2026-09-21 玩家要求：**去除构想的动画效果**——释放构想不再触发
                # 边框呼吸闪（BORDER_EVENT construct），反馈只保留气泡 + 音效。
                # 构想使用结果走临时弹窗（成功/失败都提示），锚点 = 该构想所在屏幕行。
                self.show_toast(ability_result.message, self._selected_panel_row_screen_y())
                # 左键/Enter 激活被拒（冷却/想象力不足）时同时给出面板反馈。
                if ability_result.changed and self.config.get("sfx_enabled"):
                    sfx.play("construct", volume=int(self.config.get("sfx_volume")) / 10)
                self.refresh_view()
                return
            if key_hint.startswith("action:"):
                offset = int(key_hint.split(":", 1)[1])
                actions = self._actions_for(self.context_menu_target)
                if not (0 <= offset < len(actions)):
                    self.show_toast(tr("这一行现在没有可执行的操作。"),
                                    self._selected_panel_row_screen_y())
                    self.refresh_view()
                    return
                action = actions[offset]
            else:
                self.refresh_view()
                return
            if action.startswith("攻击"):
                self._confirm_or_attack(self.context_menu_target)
            elif action == "拾取":
                self.try_pickup(self.context_menu_target)
            elif action == "回应":
                self._apply_interact()
            elif action == "移动":
                self._left_click(self.context_menu_target)
            elif action == "打开":
                self._apply("open", *self.context_menu_target)
            elif action in ('熄灭光源','点亮光源'):
                self._apply('toggle_light',*self.context_menu_target)
            elif action=='拨开门纹':
                self._apply('operate_gate_control',*self.context_menu_target)
            elif action == "重置本层机关":
                self.path.clear()
                self.observe_walk_path.clear()
                self._apply("reset_puzzle")
                self.context_menu_target = None
                self.panel_mode = "world"
        self.refresh_view()

    def _direction_map(self) -> dict[str, tuple[int, int]]:
        """方向键 → 位移。含小键盘/别名与设置页里自定义的四向键。

        走世界、走面板选中、走观察模式的 ? 都共用这一张表——同一个按键在
        哪个上下文里都不该是另一个方向。
        """
        directions = {
            "up": (0, -1), "8": (0, -1), "num8": (0, -1), "kp8": (0, -1),
            "down": (0, 1), "2": (0, 1), "num2": (0, 1), "kp2": (0, 1),
            "left": (-1, 0), "4": (-1, 0), "num4": (-1, 0), "kp4": (-1, 0),
            "right": (1, 0), "6": (1, 0), "num6": (1, 0), "kp6": (1, 0),
            "7": (-1, -1), "num7": (-1, -1), "kp7": (-1, -1), "home": (-1, -1),
            "9": (1, -1), "num9": (1, -1), "kp9": (1, -1), "pageup": (1, -1),
            "1": (-1, 1), "num1": (-1, 1), "kp1": (-1, 1), "end": (-1, 1),
            "3": (1, 1), "num3": (1, 1), "kp3": (1, 1), "pagedown": (1, 1),
        }
        for setting_key, direction in (
            ("key_up", (0, -1)),
            ("key_down", (0, 1)),
            ("key_left", (-1, 0)),
            ("key_right", (1, 0)),
        ):
            directions[str(self.config.get(setting_key)).lower()] = direction
        return directions

    def _panel_shortcut_for(self, key: str, character: str | None, aliases: set = frozenset()) -> str | None:
        """这个键要切到哪个右侧面板（不切则 None）。"""
        from ...controls import panel_for_key
        return panel_for_key(key, character, aliases)
    def _select_codex_category(self, delta: int, progress) -> None:
        """图鉴 ←→：切换分类并让条目选中项在分类内归位。

        分类层与条目层共用：分类光标与「当前分类」同步走，右侧条目列表与详情
        立刻跟着换，所以不必再按 Tab 回分类层挑分类。
        """
        self.codex_page.select_category(delta)
        self.codex_page.move_entry(
            0,
            self.catalog_definitions,
            progress,
            viewport_size=self._codex_viewport_size(),
        )

    def _handle_newgame_key(self, key: str) -> None:
        """开局选项页键位：调律（滑条/开关/难度条）与择碎片两阶段。

        q/escape 走 _newgame_cancel（碎片页退回调律、调律页退回存档槽页）。
        """
        from ...core.run_options import SLIDER_DEFS, TOGGLE_DEFS, option_rows

        # 记忆编号输入框获得焦点时：Esc/Tab 退回碎片选择，其余键交给 Input。
        try:
            seed_input = self.query_one('#newgame-seed', Input)
        except Exception:
            seed_input = None
        if seed_input is not None and self.focused is seed_input:
            if key in ('escape', 'tab'):
                self._mark_key_handled(key)
                self.set_focus(None)
                self.query_one('#newgame-content').focus()
                return
            return

        shortcut = {'r': 'reset', 'g': 'random', 'c': 'next'}.get(key)
        if shortcut:
            button = self.query_one('#newgame-' + shortcut)
            if not button.disabled:
                self._mark_key_handled(key)
                self.handle_button_press(button)
            return

        if key in ("q", "escape"):
            # escape 是底栏绑定、on_key 之后还会派发一次 action_cancel_ui——
            # 不标记已处理会被消费两次（碎片页一次 Esc 直接退回存档槽页）。
            self._mark_key_handled("escape")
            self._newgame_cancel()
            return
        if self.newgame_phase == 'identity':
            from ..dream_types import birth_key
            birth_key(self, key)
            return
        if self.newgame_phase == "fragment":
            if key in ("t", "T"):
                # 第三阶段：T 聚焦底部的「记忆编号（选填）」输入框。
                self._mark_key_handled(key)
                try:
                    self.query_one("#newgame-seed", Input).focus()
                except Exception:
                    pass
                return
            count = len(self.newgame_fragments)
            if count:
                if key in ("up", "w", "8", "num8", "kp8"):
                    self.newgame_fragment_cursor = max(0, self.newgame_fragment_cursor - 1)
                elif key in ("down", "s", "2", "num2", "kp2"):
                    self.newgame_fragment_cursor = min(count - 1, self.newgame_fragment_cursor + 1)
                elif key in ("enter", "return"):
                    self._mark_key_handled("enter")
                    self._confirm_newgame_fragment()
                    return
            self.refresh_view()
            return
        rows = option_rows()
        if key in ("up", "w", "8", "num8", "kp8"):
            self.newgame_cursor = (self.newgame_cursor - 1) % len(rows)
        elif key in ("down", "s", "2", "num2", "kp2"):
            self.newgame_cursor = (self.newgame_cursor + 1) % len(rows)
        elif key in ("left", "a", "4", "num4", "kp4"):
            kind, row_key = rows[self.newgame_cursor]
            if kind == "slider":
                self.newgame_sliders[row_key] = max(0, self.newgame_sliders[row_key] - 1)
            elif kind == "toggle":
                self._toggle_newgame_option(row_key)
        elif key in ("right", "d", "6", "num6", "kp6"):
            kind, row_key = rows[self.newgame_cursor]
            if kind == "slider":
                spec = SLIDER_DEFS[row_key]
                self.newgame_sliders[row_key] = min(len(spec["tiers"]) - 1, self.newgame_sliders[row_key] + 1)
            elif kind == "toggle":
                self._toggle_newgame_option(row_key)
        elif key in ("enter", "return", "space"):
            kind, row_key = rows[self.newgame_cursor]
            if kind == "slider":
                spec = SLIDER_DEFS[row_key]
                self.newgame_sliders[row_key] = (self.newgame_sliders[row_key] + 1) % len(spec["tiers"])
            elif kind == "toggle":
                self._toggle_newgame_option(row_key)
            else:
                # 末行「就这样入梦」：掷碎片候选，进入择一阶段。
                if key in ("enter", "return"):
                    self._mark_key_handled("enter")
                self._confirm_newgame_options()
                return
        self.refresh_view()

    def _handle_codex_key(self, key: str) -> None:
        progress = self.catalog_progress()
        if key in ("q", "escape"):
            self._codex_back()
            return
        # ←→ 直接切分类（两个层都生效，见 _select_codex_category）。
        if key in ("left", "a", "4", "num4", "kp4"):
            self._select_codex_category(-1, progress)
            self.refresh_view()
            return
        if key in ("right", "d", "6", "num6", "kp6"):
            self._select_codex_category(1, progress)
            self.refresh_view()
            return
        if key == "tab":
            if self.codex_page.focus_layer == "entries":
                self.codex_page.focus_categories()
            else:
                self.codex_page.activate_category()
                self.codex_page.move_entry(
                    0,
                    self.catalog_definitions,
                    progress,
                    viewport_size=self._codex_viewport_size(),
                )
        elif self.codex_page.focus_layer == "categories":
            # 分类层：↑ 上一个分类（与 ← 等价）、↓/Enter 进入条目列表。
            if key in ("up", "8", "num8", "kp8"):
                self._select_codex_category(-1, progress)
            elif key in ("down", "2", "num2", "kp2", "enter", "return", "space"):
                self.codex_page.activate_category()
                self.codex_page.move_entry(
                    0,
                    self.catalog_definitions,
                    progress,
                    viewport_size=self._codex_viewport_size(),
                )
        elif key in ("up", "w", "8", "num8", "kp8"):
            self.codex_page.move_entry(
                -1,
                self.catalog_definitions,
                progress,
                viewport_size=self._codex_viewport_size(),
            )
        elif key in ("down", "s", "2", "num2", "kp2"):
            self.codex_page.move_entry(
                1,
                self.catalog_definitions,
                progress,
                viewport_size=self._codex_viewport_size(),
            )
        self.refresh_view()

    def _handle_settings_key(self, key: str, character: str | None) -> None:
        if self.settings_page.capture_target is not None:
            if key in ("q", "escape"):
                self.settings_page.cancel_capture()
            else:
                self.settings_page.capture(self.config, key if '+' in key else character or key)
            self.refresh_view()
            return
        if key in ("q", "escape"):
            self._settings_back()
        elif key in ("up", "w", "8", "num8", "kp8"):
            self.settings_page.move(-1, self.config.registry)
            self.refresh_view()
        elif key in ("down", "s", "2", "num2", "kp2"):
            self.settings_page.move(1, self.config.registry)
            self.refresh_view()
        elif key in ("left", "a", "4", "num4", "kp4"):
            self.settings_page.adjust(self.config, -1, self.config.registry)
            self._sync_equipment_syntax()
            self.refresh_view()
        elif key in ("right", "d", "6", "num6", "kp6"):
            self.settings_page.adjust(self.config, 1, self.config.registry)
            self._sync_equipment_syntax()
            self.refresh_view()
        elif key in ("enter", "return", "space"):
            self.settings_page.activate(self.config, self.config.registry)
            self._sync_equipment_syntax()
            self.refresh_view()
    def on_key(self, event) -> None:
        key = event.key
        character = getattr(event, "character", None)
        aliases = set(getattr(event, "aliases", ()))
        # Enter/n/b 的底栏绑定会在 on_key 之后被触发一次（Textual 的派发顺序：
        # on_key 先于非 priority 绑定动作）。这里先清空「已处理」集合，再由
        # 各个分支把真正处理掉的键记进去，供 action_* 吃掉那次重复触发；
        # 每次按键都重置，确保底栏点击（不经过 on_key）永远能正常生效。
        self._keys_handled_in_on_key.clear()
        # 任意按键提前取消地图临时气泡（2026-09-19；标题栏播报走自己的 3 秒节奏）。
        # 必须放在所有分支之前：Alt 面板键会在 _handle_panel_shortcut 里提前 return，
        # 旧位置（分支之后）会让这些键留着气泡不散。Tab 由 Textual 的 Screen 绑定
        # 先吃掉，走不到 on_key，另由 DreamApp.action_focus_next 补收。
        self._dismiss_transient()
        # R must not act after this same event dismisses a left overlay.
        if key == 'r' and any(getattr(self, attr, None) is not None for attr in self.LEFT_OVERLAY_ATTRS):
            self._mark_key_handled(key)
        if self._handle_panel_shortcut(event):
            return
        if self._self_audit_visible():
            self._self_audit_key(key)
            self._mark_key_handled(key)
            event.stop()
            event.prevent_default()
            return
        if self._signal_key(key):
            event.stop()
            event.prevent_default()
            return
        if getattr(self,'_image_output_error','') and self.config.get('map_display') != 'character':
            if key == 'f2':
                self.action_image_preview()
            self._mark_key_handled(key)
            event.stop()
            event.prevent_default()
            return
        if key in ('f2','f3') and self.layer_observation is None:
            # These entries must precede editor input ownership, so a draft can
            # be inspected without closing it or consuming the editor's local V.
            if key == 'f2':
                self.action_image_preview()
            else:
                self.action_cycle_map_observe()
            self._mark_key_handled(key)
            event.stop()
            event.prevent_default()
            return
        if self._layer_key(key):
            self._mark_key_handled(key)
            event.stop()
            event.prevent_default()
            return
        if (getattr(self,'world_tamper_editor',None) is not None
                or self.tamper_editor is not None):
            if getattr(self,'world_tamper_editor',None) is not None:
                self.handle_world_tamper_key(key)
            else:
                self.handle_tamper_key(key)
            self._mark_key_handled(key)
            event.stop()
            if hasattr(event,'prevent_default'):
                event.prevent_default()
            return
        if hasattr(self, '_handle_qol_key') and self._handle_qol_key(event):
            return
        # 地图侧篡改浮层打开时已在更早的分支吃掉所有键；2026-10-23 起它
        # 不再占用 panel_mode，右侧面板保持原界面（是否处于篡改态只看 editor 引用）。


        # 自我察觉面板（docs §10.6）：面板打开时先处理分类/选择/展开/关闭，
        # 避免方向键继续移动角色、Enter 触发场上动作。
        if (getattr(self, "_self_audit_visible", None)
                and self._self_audit_visible()
                and self._self_audit_key(key)):
            self._mark_key_handled(key)
            event.stop()
            if hasattr(event, "prevent_default"):
                event.prevent_default()
            return
        # 任意按键提前取消地图临时气泡已在上方统一处理（2026-10-22）。
        self._expire_attack_confirmation(refresh=False)
        if self.sentence_aim is None and self.aiming and self.aim_key(key):
            self._mark_key_handled(key)
            event.stop()
            return
        if self.sentence_aim is not None and self._sentence_aim_key(key):
            self._mark_key_handled(key)
            event.stop()
            return
        if self.equipment_choice is not None:
            pending = self.equipment_choice
            if key in ('escape', 'q'):
                self.equipment_choice = None
            elif key in ('up', 'w'):
                pending['cursor'] = max(0, pending['cursor'] - 1)
            elif key in ('down', 's'):
                pending['cursor'] = min(len(pending['options']) - 1, pending['cursor'] + 1)
            elif key in ('enter', 'return', 'space'):
                self._choose_equipment_action(pending['cursor'])
            elif key in tuple(str(n) for n in range(1, 10)):
                self._choose_equipment_action(int(key) - 1)
            self._mark_key_handled(key)
            event.stop()
            self.refresh_view()
            return
        # 进层演出中：锁死一切输入，任一键 = 跳过（设计文档 §2.3）。
        if getattr(self, "_floor_transition", None) is not None:
            self._finish_floor_transition(suppress_wipe=False)
            # 标记「本键已由跳过消费」：Textual 随后还会按绑定链再跑一次
            # action_*（on_key 先于非 priority 绑定）。不标记的话，这次 Esc
            # 会顺手打开暂停菜单、n/b 会再下一层、g 会再捡一次——跳过必须
            # 完整吞掉这个键，只留「显示最终新帧、解锁」。
            self._mark_key_handled(key)
            return
        # 「先退出、再行动」完全靠顺序实现：关面板的分支自己 return，把本次输入
        # 消耗掉；用户再按一次才会落到下面的行动分发。因此这里不需要任何
        # 「下一次才生效」的跨输入标记——那种状态很容易泄漏到后续输入上。
        if key in ("enter", "return"):
            self._mark_key_handled(key)
        # 结局演出展示中：任意键 = 快进到尾声；尾声里任意键 = 返回主页。
        state = self.session.state
        if state.run_over and state.ending_id and getattr(self.app, "ending_shown", False):
            try:
                settlement = self.query_one("#settlement")
            except Exception:
                settlement = None
            if settlement is not None and settlement.active and not settlement.finished:
                settlement.skip()
                self._audio_skipped_run = state
                self.refresh_view()
                return
            if settlement is not None and key in ("up", "down", "pageup", "pagedown"):
                direction = -1 if key in ("up", "pageup") else 1
                settlement.scroll_relative(y=direction * (8 if "page" in key else 3), animate=False)
                return
            if key in ("r", "t") and self.app._retry_finished_run(tutorial=key == "t"):
                return
            self.app._return_home()
            self.app.ending_shown = False
            return
        # 携带意象·联想盘编辑器（2026-10-09，设计方案 §8.4）：整屏模态——
        # 打开时吃掉**所有**键（未匹配的键也 return，不落到世界或原面板），
        # 编辑布局时顺手走一步／发射一次是明确禁止的。q 走 action_context_q
        # （priority 绑定先于 on_key），这里不重复处理。
        if not self.home_mode and self.panel_mode == "board_editor":
            self.handle_board_editor_key(key)
            return
        # 全屏暂停菜单（2026-09-20）：模态——打开时吃掉所有键，不穿透到世界。
        # WS/↑↓/滚轮挪光标（滚轮见 on_mouse_scroll_*），Enter/空格触发，
        # Esc/Q = 继续（「返回」语义对自己也成立：菜单本身就是「最上层界面」）。
        if not self.home_mode and self.panel_mode == "pause":
            if key in ("up", "w", "8", "num8", "kp8"):
                self.pause_move(-1)
            elif key in ("down", "s", "2", "num2", "kp2"):
                self.pause_move(1)
            elif key in ("enter", "return", "space"):
                self._mark_key_handled(key)
                self.activate_pause_option()
            elif key in ("escape", "q"):
                self._mark_key_handled("escape")
                self.close_pause_menu()
            return
        # 暂停菜单里打开的设置页：与主页设置同一套键位（_handle_settings_key），
        # 只是 Q/Esc 的「返回」落在暂停菜单（_settings_back 按 settings_from 分流）。
        # Esc 必须在这里标记已处理：否则底栏 Esc 绑定随后触发取消链，
        # 会把「回暂停菜单」再推一步变成「继续游戏」。
        if not self.home_mode and self.panel_mode == "pause_settings":
            if key in ("escape", "q"):
                self._mark_key_handled("escape")
            self._handle_settings_key(key, character)
            return
        # 投掷瞄准态 Esc：取消投掷，物品不消耗（标记已处理，Esc 链不再动作）。
        if self.aiming and self.throw_item_index is not None and key == "escape":
            self._mark_key_handled("escape")
            self.throw_item_index = None
            self.aiming = False
            self.panel_mode = "world"
            self.refresh_view()
            return
        # 容器浮层（玻璃瓶/试管/气球/理想气体容器）：1 盛装、2 倒出、Esc 收起。
        # 浮层挂在左侧（map-overlay），行囊面板保持不动——收起后仍留在行囊。
        if getattr(self, "container_index", None) is not None:
            index = self.container_index
            if key in ("escape", "q"):
                # 标记已处理：Esc 链不得顺手把行囊面板也关掉（要留在行囊）。
                self._mark_key_handled("escape")
                self.container_index = None
                self.refresh_view()
                return
            if key in ("1", "num1", "kp1"):
                self._apply("container_fill", index)
                self.refresh_view()
                return
            if key in ("2", "num2", "kp2"):
                self._apply("container_pour", index)
                self.refresh_view()
                return
            return
            return
        # 篡改编辑中（规格 §4.4）：所有按键都归篡改控制器——数字与 Enter 不再
        # 触发对话交易，Esc 按「预览 → 位置 → 词表 → 收面板」逐级退。
        # 必须逐键打标记：底栏绑定紧跟在 on_key 之后，漏标记就会一次按键干两件事。
        # 位置要排在 ~ / o \ [ ] 这些「全局界面开关」之前：它们各自改的是光标锁定、
        # 目标辅助、详情展开等状态，编辑期间被顺手改掉＝草稿还开着、界面已经变了。
        # 真正的模态（进层演出、结局、联想盘、暂停菜单、容器浮层）仍排在前面——
        # 它们与篡改面板互斥，不可能同时开着。
        if self.tamper_editor is not None:
            self.handle_tamper_key(key)
            self._mark_key_handled(key)
            return
        # 锁定键归一：物理键 ` 与 ~ 是同一个键，终端按 Shift 与否会把它报成两个
        # 不同键名（裸 ` = grave_accent、Shift+` = tilde），只绑一个键名时另一个
        # 键毫无反应——「按 ~ 锁定无效」的根因。这里两种键名与两种字符都当同一个
        # 键处理，并标记 tilde 已处理，吃掉紧随其后的底栏「~」绑定那次触发，
        # 保证一次按键只切换一次（底栏键位只需登记一条）。
        if key in ("tilde", "grave_accent", "grave", "backtick") or character in ("~", "`"):
            if key == "tilde":
                # 只有键名 tilde 会命中底栏那条「~」绑定，需要标记以免切两次；
                # 裸 ` 报成 grave_accent、根本不产生绑定触发，此时不能留标记——
                # 陈旧标记会吃掉下一次底栏「锁定」点击（点了没反应）。
                self._mark_key_handled("tilde")
            self.toggle_cursor_lock()
            return
        # 「/」强制切换光标所属区域（2026-10-12）：地图 → 右侧面板 →（浮层）
        # 循环。切换后「对应的默认按键」只在焦点区域内生效——zone=panel 时
        # 方向键与 WASD 一样只动面板光标（解锁态也能 ←→ 切页，见 directions
        # 分支的 zone 检查）。原「/ 开操作面板」的触发让位给 ? 与 h；主页与
        # 观察模式（? 光标自成体系）不参与。标记已处理：底栏「/」绑定随后
        # 触发一次，不标记会连切两次。
        if key == "slash" and not self.home_mode and not self.observe_mode:
            self._mark_key_handled("slash")
            self.cycle_cursor_zone()
            return
        # 「\」是最优先的界面开关：它要能在任何面板、乃至寻路进行中随时生效，
        # 因此排在「任意按键刹停寻路」之前（否则路径激活时第一次按 \ 会被吃掉）。
        # （原 Alt 因裸 Alt 在 VT 终端不产生按键记录而无法在真机使用，已改绑 \；
        #  Alt 组合仍由原生监视器拦截为无害的 alt 键，避免误触保存退出。）
        # o 键：瞄准态=瞄准辅助（自动指向/循环异像）；否则开关目标辅助。
        if key == "o":
            self._mark_key_handled("o")
            self.assist_key()
            return
        if key in ("backslash",) or character == "\\":
            self.details_expanded = not self.details_expanded
            if self.cell_detail_target is not None:
                # 格子详情里 \ 只管「介绍行」的收放：整个面板的内容不受影响。
                self.cell_detail_intros = not self.cell_detail_intros
            self.refresh_view()
            return
        # ' 键：行囊页选中条目后打开左侧物品菜单；观测页则打开意象详情；
        # 观察模式打开 ? 所在格的格子详情。
        if key in ("'", "apostrophe", "quote"):
            if self.observe_mode:
                if self.observe_cursor is not None:
                    self.open_cell_detail(self.observe_cursor)
                return
            if self.panel_mode in ("inventory", "equipment", "catalog"):
                state = self.session.state
                if self.panel_mode == "catalog":
                    self._open_anomaly_detail(max(0, min(self.panel_selection, len(state.visible_anomalies()) - 1)))
                    return
                if state.inventory:
                    if self.panel_mode == "equipment":
                        equipment_indices = [index for index, item in enumerate(state.inventory) if item.slot]
                        if not equipment_indices:
                            return
                        index = equipment_indices[min(self.panel_selection, len(equipment_indices) - 1)]
                    else:
                        if self.panel_selection not in self._inventory_visible_indices():
                            return
                        index = self.panel_selection
                    self._open_item_menu(index)
                return
        # [ 键：携带意象页直接打开联想盘编辑器（§8.4「从原列表装配」的键盘入口，
        # 空手进去，可以只整理线材与插片）。] 已被「武装下一次左键」占用，
        # 这里刻意选它的配对键，不用 Tab（行囊快捷键）也不用 F1–F12。
        if key in ("[", "left_square_bracket", "bracket_left"):
            if self.panel_mode == "equipment" and not self.home_mode:
                self._mark_key_handled("[")
                self.open_board_editor()
            return
        # ] 键武装下一次面板左键：只切换该条展开/收起（原 Shift+左键语义）。
        if key in ("]", "bracket_right"):
            self._bracket_armed = not self._bracket_armed
            self.refresh_view()
            return
        if self._bracket_armed:
            self._bracket_armed = False  # 任意其他按键解除武装
        # 洞察替换面板打开时：↑↓ 选要换掉的洞察，Enter 确认替换，Esc/Q 进入
        # 「确定放弃替换吗？」二次确认（不直接退出）。其余按键不穿透到游戏。
        if self.insight_replace_target is not None:
            if self.insight_replace_confirm_discard:
                if key in ("enter", "return", "y"):
                    self._mark_key_handled(key)
                    self.activate_insight_replace()
                elif key in ("n",):
                    self.cancel_discard_insight()
                elif key in ("q", "escape"):
                    # 二次确认里再按 Esc＝「否」，回到替换列表。
                    self._mark_key_handled("escape")
                    self.cancel_discard_insight()
                return
            if key in ("up", "w", "8", "num8", "kp8"):
                self.move_insight_replace_cursor(-1)
                return
            if key in ("down", "s", "2", "num2", "kp2"):
                self.move_insight_replace_cursor(1)
                return
            if key in ("enter", "return"):
                self._mark_key_handled(key)
                self.activate_insight_replace()
                return
            if key in ("q", "escape"):
                # 不直接退出：先把 Esc/Q 转成「放弃确认」这一步。
                self._mark_key_handled(key)
                self.request_discard_insight()
                return
            return
        # 记忆碎片替换面板：与洞察替换面板同构的键位。
        if self.memory_replace_target is not None:
            if self.memory_replace_confirm_discard:
                if key in ("enter", "return", "y"):
                    self._mark_key_handled(key)
                    self.activate_memory_replace()
                elif key in ("n",):
                    self.cancel_discard_memory()
                elif key in ("q", "escape"):
                    # 二次确认里再按 Esc＝「否」，回到替换列表。
                    self._mark_key_handled("escape")
                    self.cancel_discard_memory()
                return
            if key in ("up", "w", "8", "num8", "kp8"):
                self.move_memory_replace_cursor(-1)
                return
            if key in ("down", "s", "2", "num2", "kp2"):
                self.move_memory_replace_cursor(1)
                return
            if key in ("enter", "return"):
                self._mark_key_handled(key)
                self.activate_memory_replace()
                return
            if key in ("q", "escape"):
                # 不直接退出：先把 Esc/Q 转成「放弃确认」这一步。
                self._mark_key_handled(key)
                self.request_discard_memory()
                return
            return
        # 物品菜单（左侧覆盖面板）打开时：
        #   · 三套键位（方向键/WASD/小键盘）只移动菜单光标——菜单本身就是「默认锁定」；
        #   · U / D 是**菜单自己的功能键**（携带/卸下/使用、放下），按下即执行，
        #     等同于左键点那一行；它们优先于「WASD 当方向」的解释（菜单里 D 不是右移）；
        #   · Q/Esc 放行给绑定层关闭（在这里先关会让动作接着往下走，一次 Esc 关两层）；
        #   · 其余按键只关面板、不行动——想行动得再按一次。
        if self.item_menu_target is not None:
            if key in ("q", "escape"):
                return
            if key in self.MENU_ACTION_KEYS or self._item_menu_action_for(key) is not None:
                # 面板自己的功能键：按下即执行（同左键点该行按钮），执行完按菜单规则收尾。
                # 物品专属副动作（如镁光火柴的原地点燃）也只在该行真实列出时才认。
                self.activate_item_menu(key)
                return
            if key in self.LOCKED_MOVE_KEYS or key in ("pageup", "pagedown", "home", "end"):
                self._move_menu_cursor(key)
                return
            # 面板之外的按键：只关面板、不行动，想行动得再按一次。
            self.close_item_menu()
            self.refresh_view()
            return
        # 观测详情打开时：↑↓ 在字段间移动光标并随之滚动，PgUp/PgDn 翻页；
        # Q/Esc 同样只放行（由 action_save_exit / action_context_q 关闭），
        # 其余按键沿用物品菜单的手感——关掉面板再交给游戏。
        if self.anomaly_detail_target is not None:
            if key in ("up", "w", "8", "num8", "kp8"):
                self._move_anomaly_detail(-1)
                return
            if key in ("down", "s", "2", "num2", "kp2"):
                self._move_anomaly_detail(1)
                return
            if key in ("pageup", "9", "num9", "kp9"):
                self._scroll_anomaly_detail(self._anomaly_detail_viewport())
                return
            if key in ("pagedown", "3", "num3", "kp3"):
                self._scroll_anomaly_detail(-self._anomaly_detail_viewport())
                return
            if key in ("q", "escape"):
                return
            self.close_anomaly_detail()
            return
        # 拾取面板打开时：↑↓ 挪光标、空格勾选、A 全选、Enter 捡起、滚轮滚动。
        # 与其它左侧面板一样默认锁定——面板之外的按键只关面板、不行动。
        if self.pickup_target is not None:
            if key in ("up", "w", "8", "num8", "kp8"):
                self.move_pickup_cursor(-1)
                return
            if key in ("down", "s", "2", "num2", "kp2"):
                self.move_pickup_cursor(1)
                return
            if key in ("pageup", "9", "num9", "kp9"):
                self.scroll_pickup(1)
                return
            if key in ("pagedown", "3", "num3", "kp3"):
                self.scroll_pickup(-1)
                return
            if key == "space":
                self.toggle_pickup_selection()
                return
            if key == "a":
                self.select_all_pickups()
                return
            if key in ("enter", "return"):
                self._mark_key_handled("enter")
                self.activate_pickup()
                return
            if key in ("g", "G"):
                # 面板里再按一次 G = 结算勾选（与单独按 G 拾取的手感一致），
                # 而不是被下面的兜底当成「其它键」把面板关掉、什么都不拿。
                # 必须打标记：底栏「捡起」绑定紧跟 on_key 之后，否则会再捡一次。
                self._mark_key_handled(key)
                self.activate_pickup()
                return
            if key in ("q", "escape"):
                return
            self.close_pickup()
            return
        # 复合事件对话面板：数字直接选选项；↑↓ 挪光标 + Enter 确认；
        # PgUp/PgDn 与滚轮滚动对话文字；Esc/X 收起对话（事件保持未解）。
        if self.panel_mode == "event_dialog":
            if key == self._tamper_key_label().lower():
                # 篡改键只在对话上下文里生效（§4.1）；没有合法位置时不弹面板。
                if self.open_tamper_editor():
                    self._mark_key_handled(key)
                return
            npc = self.session.state.pending_npc()
            event = self.session.state.pending_event()
            # NPC 的选项表由**这名 NPC 抽到的那几项**决定（实体上记着下标，
            # 见 core.content.npc_options_for），不是整张职业交易表。
            if npc:
                from ...core.content import npc_visible_options
                option_count = len(npc_visible_options(state, npc))
            else:
                option_count = len(event.options) if event else 0
            cursor = getattr(self, "event_dialog_cursor", 0)
            if key in ("escape", "x", "q"):
                # 关掉的键必须标记已处理：否则 Esc 链随后走空（对话已收、
                # 面板已回世界）会顺手打开暂停菜单，一次按键干两个动作。
                self._mark_key_handled(key)
                self._close_event_dialog_state()
                self.panel_mode = "world"
                self.refresh_view()
                return
            if key in ("enter", "return"):
                if option_count:
                    self._mark_key_handled("enter")
                    self._choose_dialog_option(cursor)
                return
            if key in ("up", "w"):
                self.event_dialog_cursor = max(0, cursor - 1) if option_count else 0
                self.refresh_view()
                return
            if key in ("down", "s"):
                self.event_dialog_cursor = min(max(0, option_count - 1), cursor + 1) if option_count else 0
                self.refresh_view()
                return
            digit = {"1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6, "8": 7, "9": 8}.get(key.lstrip("numkp_")[-1:] if key[:3] in ("num", "kp_") else key)
            if digit is not None and digit < option_count:
                self.event_dialog_cursor = digit
                self._mark_key_handled(key)
                self._choose_dialog_option(digit)
                return
            if key in ("pageup", "9"):
                self.event_dialog_scroll = max(0, self.event_dialog_scroll - 5)
                self.refresh_view()
                return
            if key in ("pagedown", "3"):
                self.event_dialog_scroll += 5
                self.refresh_view()
                return
            return
        # 格子详情打开时：与意象详情同一套手感——↑↓ 挪光标、PgUp/PgDn 翻页、
        # 滚轮滚动；Q/Esc 由绑定层关闭（先于 on_key），其余按键关闭面板后
        # 再交给游戏，不做任何多余动作。
        if self.cell_detail_target is not None:
            if key in ("up", "w", "8", "num8", "kp8"):
                self._move_anomaly_detail(-1)
                return
            if key in ("down", "s", "2", "num2", "kp2"):
                self._move_anomaly_detail(1)
                return
            if key in ("pageup", "9", "num9", "kp9"):
                self._scroll_anomaly_detail(self._anomaly_detail_viewport())
                return
            if key in ("pagedown", "3", "num3", "kp3"):
                self._scroll_anomaly_detail(-self._anomaly_detail_viewport())
                return
            if key in ("q", "escape"):
                return
            if key == "enter":
                # 子详情/展开：吞掉这一次输入，零消耗、不穿透到游戏（§16.6）。
                self._cd_activate_row()
                return
            self.close_cell_detail()
            return
        if self.panel_locked and self.item_menu_target is None and self.anomaly_detail_target is None and self.cell_detail_target is None:
            # 面板锁定：三套键位（方向键 / WASD / 小键盘）只移动面板光标，
            # 绝不动游戏/地图。覆盖面板打开时先处理面板自身按键（菜单优先于锁定）。
            if self._handle_locked_keys(key, character):
                return
        # 测试模式调试面板（2026-09-18）：面板打开时它是模态的，吃掉所有键。
        # ⚠️ 位置必须在「观察模式」之前（2026-09-21）：调试面板的执行键是**小写 l**，
        # 而观察模式会把所有按键收进 _handle_observe_key——排在其后的话，
        # 「观察 ? 指定目标格 + 传送」这条组合根本收不到 l，也就谈不上「? 优先」。
        if self.test_mode and self.debug_panel_open:
            self._handle_debug_key(key, character)
            return
        if self.observe_mode and key in ('p', 'alt+p'):
            target = self.observe_cursor
            if target is not None:
                if key == 'p':
                    self.pinned_target = None if self.pinned_target == target else target
                elif target in self.shortcut_targets:
                    self.shortcut_targets.remove(target)
                else:
                    self.shortcut_targets.append(target)
                self.refresh_view()
            return
        if self.observe_mode:
            # 观察模式：世界完全静止——自己不挪步、时间不推进、视野不重算。
            # 所有按键都收在 _handle_observe_key 里，只做「挪 ? / 切界面 / 退出
            # 观察」三件事，绝不落到任何 session.apply。位置放在覆盖面板
            # （物品菜单/意象详情）与「\」「]」之后：那几个是纯界面开关，
            # 观察时也该照常可用。
            self._handle_observe_key(key, character)
            return
        # 左侧覆盖面板（物品菜单/意象详情/格子详情）＝ 默认锁定：
        # 三套键位都只移动面板光标，其余按键**只关面板、不行动**——想行动得再按一次。
        # 退出/切换类按键（q/esc/') 与折叠(\) 例外，它们本来就只关面板。
        # ⚠️ 替换洞察 / 替换记忆是「不可打断」的：除了面板自己的选中确认，
        # 其他键与点击一律吞掉（既不关面板也不行动），防止误触丢掉待定条目。
        # ⚠️ 必须排在 `if self.path` 之前：否则「面板开着 + 路径激活」时一次按键
        # 会先被寻路刹停吃掉，面板留到下一次按键才关，退化成「要按两次」。
        # ⚠️ 这里**不设**「下次才生效」的标记：关面板就 return 掉了，本次按键
        # 已经被消耗，第二次按自然落到下面的行动分发——不需要额外状态。
        active_overlay = self._active_left_overlay()
        if active_overlay is not None and not self.panel_locked:
            if self._left_overlay_blocks_interrupt():
                if key not in ("q", "escape"):
                    self.refresh_view()
                    return
            elif key in self.LOCKED_MOVE_KEYS:
                self._locked_panel_key(key)
                return
            else:
                # Esc 在这里只负责关面板：标记已处理，否则底栏 Esc 绑定随后
                # 触发取消链——面板刚被这里收掉，链一路走空会顺手打开暂停菜单，
                # 一次按键干两个动作。
                if key == "escape":
                    self._mark_key_handled("escape")
                self.path.clear()
                self.observe_walk_path.clear()
                self.pickup_goal = None
                self._close_active_left_overlay()
                self.refresh_view()
                return
        if self.path:
            # 鼠标寻路是连续动作；任意按键只负责立即刹停，不额外移动或消耗回合。
            # Esc 同上：刹停就是刹停（角色静止），暂停菜单要再按一次才开。
            if key == "escape":
                self._mark_key_handled("escape")
            self.path.clear()
            self.observe_walk_path.clear()
            self.pickup_goal = None
            self.refresh_view()
            return
        if self.home_mode and self.panel_mode == "home_history":
            # 旧梦回忆页在「q/escape 早退」之前路由：Esc/Q 要能从详情退回列表、
            # 从列表退回主页。
            self._handle_history_key(key)
            return
        if not self.home_mode and self.panel_mode == "pause_codex":
            # 游戏内图鉴覆盖层（2026-10-14）：同样在 q/escape 早退之前路由——
            # Q/Esc 逐层退（条目层→分类层→暂停菜单）。覆盖层开着时到达这里
            # 的键一律不再给世界：顺手标记防底栏动作重复触发。
            self._handle_codex_key(key)
            self._mark_key_handled(key)
            return
        if self.home_mode and self.panel_mode == "home_newgame":
            # 开局选项页同样在 q/escape 早退之前路由（q 是 priority 绑定，
            # 不进这里就会被吞）。
            self._handle_newgame_key(key)
            return
        # 地图侧语句篡改（docs §15.2）：世界模式用篡改键打开面板；面板打开后的
        # 全键消费已在 on_key 顶部处理（必须早于 [ ] 被其它页消费）。
        if (not self.home_mode and self.panel_mode != "event_dialog"
                and key == self._tamper_key_label().lower()):
            if self.open_world_tamper_editor():
                self._mark_key_handled(key)
            return
        if key in ("q", "escape"):
            return
        if self.home_mode:
            if self.panel_mode == "home_catalog":
                self._handle_codex_key(key)
                return
            if self.panel_mode == "home_settings":
                self._handle_settings_key(key, character)
                return
            # 主页/存档槽页的光标：↑↓ 在「存档槽 1/2/3」与「图鉴/设置/退出」两段
            # 之间换行，←→ 在行内选左右项（存档槽 ↔ 删除、图鉴 ↔ 设置 ↔ 退出）。
            # ⚠️ Enter 在主页**不激活**光标项（2026-09-16 玩家要求：去掉「Enter 开
            # 启新游戏」）。主页的 Enter 只算「确认/左键」——光标在「删除」上时它
            # 仍是那段两段确认的一部分（见 activate_home_selection），其余位置
            # 一律不落地，必须用鼠标左键点击来载入/新建存档。
            # （小键盘数字键在主页仍用于直选槽位，见下面的 slot_aliases。）
            # ⚠️ 主页**没有地图**，小键盘无处可走地图，所以这里让数字字符
            # （数字锁定开时小键盘的真实键名）也参与光标移动——与方向键同效。
            # 顺序很重要：1/2/3 先由下面的 slot_aliases 抢走（直选槽位）。
            # 槽只有 3 个，直选比「当方向键」更有用，所以这个优先级是有意的。
            slot_aliases = {
                "1": 1, "2": 2, "3": 3,
                "num1": 1, "num3": 3,
                "kp1": 1, "kp3": 3,
            }
            if key in slot_aliases:
                if self.home_view == "menu":
                    # 主菜单上按数字 = 直达存档槽页并选中该槽（2026-09-23）。
                    self._open_saves(slot_aliases[key])
                else:
                    self.select_home_slot(slot_aliases[key])
                self.refresh_view()
                return
            vertical = {
                # 注意这里**没有** "2"：它已在上面被 slot_aliases 抢走（直选槽 2）。
                "down": 1, "num2": 1, "kp2": 1,
                "up": -1, "8": -1, "num8": -1, "kp8": -1,
            }
            if key in vertical:
                self.move_home_cursor(vertical=vertical[key])
                return
            horizontal = {
                "right": 1, "6": 1, "num6": 1, "kp6": 1,
                "left": -1, "4": -1, "num4": -1, "kp4": -1,
            }
            if key in horizontal:
                self.move_home_cursor(horizontal=horizontal[key])
                return
            if key.lower() == "d":
                # D 键仍是「删掉当前光标所在槽」，但只在存档槽页的槽位行生效——
                # 主菜单视图没有槽位，D 不该误删上一个槽（避免误删）。
                if self.home_view == "saves" and self.home_row < self.session.manager.SLOT_COUNT:
                    self._request_delete_slot(self.selected_slot)
            elif key.lower() == "r" and getattr(self, "saves_test", False) and self.home_view == "saves":
                # 2026-10-23 测试模式专属：R = 用新的调律选项替换当前测试存档
                # （不先删档；取消调律页则旧档保持原样）。
                if self._saves_manager().for_slot(self.selected_slot).slot_exists():
                    self._open_newgame(self.selected_slot, test=True)
            elif key in ("enter", "return"):
                # 2026-09-18 恢复：Enter = 激活光标项（载入/新建存档、进图鉴/
                # 设置/退出）——与鼠标左键完全同一条路径。「删除」仍是两段确认。
                self._mark_key_handled("enter")
                self.activate_home_selection()
                return
            elif key == "k":
                self._open_codex()
                return
            elif key in ("s", "comma"):
                self._open_settings()
                return
            self.refresh_view()
            return
            if key in ("1", "num1", "kp1") and index is not None:
                self._apply("container_fill", index)
                self.refresh_view()
                return
            if key in ("2", "num2", "kp2") and index is not None:
                self._apply("container_pour", index)
                self.refresh_view()
                return
            return
        if key == "L" and self.test_mode and not self.home_mode:
            # 大写 L：调试面板开关（与放置分离）。
            self._mark_key_handled("L")
            self._debug_toggle_or_spawn()
            return
        if key == "l" and self.test_mode and not self.home_mode:
            # 小写 l：放置——有待释放物才在光标格（观察 ? / 鼠标悬停）落地。
            self._mark_key_handled("l")
            self._debug_spawn_from_target()
            return
        if self.pending_confirmation:
            if key.lower() in ("y", "enter"):
                _, target = self.pending_confirmation
                self._execute_confirmed_attack(target)
                return
            self._cancel_attack_confirmation()
            if key.lower() in ("n", "escape", "q"):
                self._mark_key_handled(key)
                return
            # Other inputs cancel the prompt and retain their ordinary action.
        # Alt+方向 = 地图缩放（原 Ctrl+方向迁移；Ctrl 序列保留兼容）。
        if key in ("ctrl+up", "ctrl+down", "alt+up", "alt+down"):
            self._zoom_map(1 if key in ("ctrl+up", "alt+up") else -1)
            return
        # 洞察之镜三选一面板：↑↓ 选择、Enter/左键 选定并消耗。
        if self.mirror_index is not None:
            if key in ("up", "w", "num8", "kp8"):
                self.mirror_cursor = max(0, self.mirror_cursor - 1)
            elif key in ("down", "s", "num2", "kp2"):
                self.mirror_cursor = min(len(self.mirror_rolls) - 1, self.mirror_cursor + 1)
            elif key in ("enter", "return", "space"):
                if self.mirror_rolls:
                    self._apply("choose_mirror_insight", self.mirror_index,
                                       self.mirror_rolls[min(self.mirror_cursor, len(self.mirror_rolls) - 1)])
                    self.mirror_index = None
            elif key in ("escape", "q"):
                self.mirror_index = None  # 收镜不消耗
            self.refresh_view()
            return
        # 喷射弹药选择浮层：↑↓ 选择、Enter/左键 选用、Esc 取消。
        if getattr(self, "spray_select", None) is not None:
            options = self.spray_select.get("options", [])
            if key in ("escape", "q"):
                self.spray_select = None
                self.aim_action_choice = None
                self._mark_key_handled(key)
            elif key in ("up", "w", "num8", "kp8"):
                self.spray_select["cursor"] = max(0, self.spray_select["cursor"] - 1)
            elif key in ("down", "s", "num2", "kp2"):
                self.spray_select["cursor"] = min(len(options) - 1, self.spray_select["cursor"] + 1)
            elif key in ("enter", "return", "space"):
                cursor = min(self.spray_select["cursor"], len(options) - 1)
                if options:
                    self._choose_spray_ammo(options[cursor][0])
            self.refresh_view()
            return
        # §8 S23 青灯祭品浮层：↑↓ 选择、空格勾选、Enter 确认三件、Esc/Q 取消。
        if self.lens_offer_scene:
            items = self.lens_offer_items
            if key in ("escape", "q"):
                self._clear_lens_offer()
                self._mark_key_handled(key)
            elif key in ("up", "w", "num8", "kp8"):
                self.lens_offer_cursor = max(0, self.lens_offer_cursor - 1)
            elif key in ("down", "s", "num2", "kp2"):
                self.lens_offer_cursor = min(len(items) - 1, self.lens_offer_cursor + 1)
            elif key == "space":
                if items:
                    self._lens_offer_toggle(items[min(self.lens_offer_cursor, len(items) - 1)][0])
            elif key in ("enter", "return"):
                self._confirm_lens_offer()
            self.refresh_view()
            return
        directions = {
            "up": (0, -1), "8": (0, -1), "num8": (0, -1), "kp8": (0, -1),
            "down": (0, 1), "2": (0, 1), "num2": (0, 1), "kp2": (0, 1),
            "left": (-1, 0), "4": (-1, 0), "num4": (-1, 0), "kp4": (-1, 0),
            "right": (1, 0), "6": (1, 0), "num6": (1, 0), "kp6": (1, 0),
            "7": (-1, -1), "num7": (-1, -1), "kp7": (-1, -1), "home": (-1, -1),
            "9": (1, -1), "num9": (1, -1), "kp9": (1, -1), "pageup": (1, -1),
            "1": (-1, 1), "num1": (-1, 1), "kp1": (-1, 1), "end": (-1, 1),
            "3": (1, 1), "num3": (1, 1), "kp3": (1, 1), "pagedown": (1, 1),
        }
        for setting_key, direction in (
            ("key_up", (0, -1)),
            ("key_down", (0, 1)),
            ("key_left", (-1, 0)),
            ("key_right", (1, 0)),
        ):
            directions[str(self.config.get(setting_key)).lower()] = direction
        selected_panel = self._panel_shortcut_for(key, character, set(getattr(event, 'aliases', ())))
        if selected_panel:
            self._toggle_panel(selected_panel)
            return
        if not self.panel_locked and key in self.WASD_PANEL_KEYS and key not in directions:
            # 兜底：config 把某个 WASD 键重映射成方向键后（它已不在 directions 里），
            # WASD 的「随时面板」职责也不能丢（2026-09-16 互换）。锁定态由上面的
            # _handle_locked_keys 处理，不会走到这里。
            if self._locked_panel_key(key):
                return
        if key in directions:
            if self.aiming and self.aim_key(key, directions):
                self._mark_key_handled(key)
                return
            direction = directions[key]
            # 分工（见 WASD_PANEL_KEYS 上方的大注释，2026-09-16 玩家拍板互换）：
            #   · 方向键（含 NumLock 关的小键盘 2468）→ 默认走地图移动；
            #   · WASD → 随时走面板选取（解锁也动面板）；
            #   · 锁定后三套都走面板。
            # 2026-10-12 补充：/ 键切到 zone=panel 时，方向键也与 WASD 同权——
            # 只动面板光标（←→ 切页、↑↓ 滚记录/选取），绝不动游戏。
            # 右侧面板不再隐式锁键：在行囊/携带意象等界面上按方向键/数字会直接
            # 走过去（感知类面板会先自动回到事件记录，那里才有可移动的选中项）。
            # 2026-09-19：征兆/观测/构想页方向键/小键盘在面板内移动选中项，
            # 不再触发地图移动、也不再把界面拉回事件记录。
            if self.panel_mode in ("portents", "catalog", "actions") and key in (
                "up", "down", "num8", "kp8", "num2", "kp2",
            ):
                move = {"up": -1, "num8": -1, "kp8": -1, "down": 1, "num2": 1, "kp2": 1}.get(key)
                self._move_panel_selection(move)
                return
            zone = getattr(self, "cursor_zone", "map")
            if (key in self.WASD_PANEL_KEYS or self.panel_locked
                    or (zone == "panel" and key in self.LOCKED_MOVE_KEYS)):
                if self._locked_panel_key(key):
                    return
            if not self._should_move_map_with_keys():
                return
            self._prepare_map_move_from_panel()
            # 长按改为“帧定时器驱动”：节拍窗口内的重复按键事件不直接触发移动，
            # 只作为“按键仍被按住”的证据（终端不发送释放事件，靠超时判定松开）；
            # 移动由 30fps 帧定时器按固定节拍执行，与渲染同步、逐格呈现。
            now = time.monotonic()
            if key == self._last_move_key and now - self._last_move_time < MOVE_REPEAT_MIN_SECONDS:
                self._held_key = key
                self._held_direction = direction
                self._last_hold_event = now
                self._hold_repeats += 1
                return
            self._last_move_key = key
            self._last_move_time = now
            self.path.clear()
            self.observe_walk_path.clear()
            self.facing = direction
            self._held_key = key
            self._held_direction = direction
            self._last_hold_event = now
            self._hold_repeats = 0
            self._move_player(*self.facing)
        elif character in ("。",) or (
            key in ("num5", "kp5", "numpad5", "5")
            and bool(self.config.get("numpad5_wait"))
        ):
            # 小键盘/全角等待别名（主键位 . 由底栏绑定 action_wait_turn 处理；
            # 按下 "." 时 event.key 为 full_stop，不能重复出现在此，否则等待两次）。
            # "5"：NumLock 开时小键盘 5 发来普通字符（ roguelike 惯例：中心键=原地等待）。
            # 是否生效由设置页「小键盘5等待」开关控制，关闭后 5 不再等待（防误触）。
            self._apply("wait")
        elif key == "e":
            self.path.clear(); self._apply_interact()
        elif key == "q":
            # 快捷投掷只「打开投掷选择」，不沿当前朝向立即扔出（§14 I3）。
            self.path.clear(); self.begin_throw_aim(0)
        elif key in ("D", "shift+d"):
            self.path.clear(); self._apply("drop", 0)
        elif key in ("W", "shift+w"):
            self.path.clear(); self._apply("equip", 0)
        elif key == "u":
            self.path.clear()
            self.observe_walk_path.clear()
            state = self.session.state
            index = next((i for i, item in enumerate(state.inventory) if item.category in ("摄入物", "易逝物", "交互道具")), None)
            if index is not None:
                result = self._apply("use", index)
                if result.data.get("container_menu") is not None:
                    self._open_container_overlay(result.data["container_menu"])
            # 2026-10-21：U 只使用物品；没有可用物品时不生成发射许可。
        elif key == "n":
            self._mark_key_handled(key)  # 底栏「下潜」绑定紧随其后，吃掉那次重复
            self.path.clear(); self._apply_floor_change("descend")
        elif key == "b":
            self._mark_key_handled(key)  # 底栏「上浮」绑定紧随其后，吃掉那次重复
            self.path.clear(); self._apply_floor_change("backtrack")
        elif key in ("enter", "return"):
            # Enter = 行动（见 _handle_action_key）：面板里激活条目；世界里只处理
            # 「相邻」事务——回应相邻异常地点、取走相邻台面（木桌子/石台）上的显化物。
            # 脚下的显化物与脚下的异常地点不归 Enter（那是 G / 走过去的事）。
            self._handle_action_key()
        elif key == "space":
            # 空格不承担「行动」：世界里保持无动作，只在面板里激活条目。
            if self.panel_mode != "world":
                self._activate_panel_selection()
        # 教程埋点：welcome 步等待任意键（所有走到这里的输入都算证据）。
        if self.session.state.tutorial.get("active"):
            self.session.state.tutorial_events.setdefault("any_input", 1)
        self.refresh_view()
    def _ui_escape_chain(self) -> bool:
        """Esc 的「取消/关闭界面」链：按优先级逐层收面板，返回是否消费了按键。

        2026-09-18 起 Esc 只做取消；保存并退出走 F10（或底栏按钮）。
        链走到头（没有任何可关的界面）返回 False——此时 Esc 不再有动作，
        误按不会把整局存档退出。
        """
        if self._active_tamper_editor() is not None:
            if getattr(self,'world_tamper_editor',None) is not None:
                self.handle_world_tamper_key('escape')
            elif not self._tamper_preview_key('escape'):
                self._tamper_escape(self.session.state)
            return True
        if getattr(self, "_self_audit_visible", None) and self._self_audit_visible():
            # 自我察觉面板开着时，Esc 只收面板，不进入 Esc 菜单。
            self._close_self_audit()
            return True
        if self.sentence_aim is not None:
            self._cancel_sentence_aim()
            self.refresh_view()
            return True
        if self.aiming:
            self.cancel_aim()
            self.refresh_view()
            return True
        if self._handled_in_on_key("escape"):
            # on_key 已经处理过这次 Esc（观察模式下 = 结束观察），别再往下走。
            return True
        if self.tamper_editor is not None:
            # 篡改编辑：Esc 逐级退（预览 → 位置 → 词表 → 收起面板），收完面板后的
            # 下一次 Esc 才轮到关对话。键盘路径已在 on_key 处理并打标记，这里兜的
            # 是底栏 Esc 点击（它不经过 on_key）。
            self._tamper_escape(self.session.state)
            return True
        if self._cancel_attack_confirmation():
            return True
        if self.lens_offer_scene:
            # §8 S23 祭品浮层：键盘路径已在 on_key 收掉，这里兜底栏 Esc 点击。
            self._clear_lens_offer()
            self.refresh_view()
            return True
        if not self.home_mode and self.panel_mode == "pause":
            # 暂停菜单本身开着：Esc = 继续（键盘路径在 on_key 里已标记处理，
            # 这里兜的是底栏 Esc 点击——它不经过 on_key）。
            self.close_pause_menu()
            return True
        if not self.home_mode and self.panel_mode == "pause_settings":
            # 暂停菜单打开的设置页：回暂停菜单；键位捕获态交给设置页自己。
            if self.settings_page.capture_target is None:
                self._settings_back()
            return True
        if not self.home_mode and self.panel_mode == "board_editor":
            # 联想盘编辑器：Esc 先松手（放回原位），手上空了才整体退出并丢弃草稿。
            # 键盘路径在 on_key 里已标记处理，这里兜的是底栏 Esc 点击。
            editor = self.board_editor
            if editor is not None and not editor.cancel_held():
                self.close_board_editor()
            elif editor is None:
                self.close_board_editor()
            else:
                self.refresh_view()
            return True
        if self.debug_panel_open:
            # 调试面板：Esc 一次退出面板，保留选中状态（下次打开还在）。
            self.debug_panel_open = False
            self.refresh_view()
            return True
        if self.insight_replace_target is not None:
            # 洞察替换面板：Esc 不直接退，先进「确定放弃替换吗？」二次确认。
            self.request_discard_insight()
            return True
        if self.memory_replace_target is not None:
            # 碎片替换面板：Esc 同样先进二次确认。
            self.request_discard_memory()
            return True
        if self.cell_detail_target is not None:
            # 格子详情优先于「结束观察」：Esc/q 先关面板，观察模式原样保留。
            self.close_cell_detail()
            return True
        if self.observe_mode:
            # 观察模式里 Esc 的语义是「结束观察」。
            self.exit_observe()
            self.refresh_view()
            return True
        if self.item_menu_target is not None:
            self.close_item_menu()
            return True
        if self.anomaly_detail_target is not None:
            self.close_anomaly_detail()
            return True
        if self.path:
            self.path.clear()
            self.observe_walk_path.clear()
            self.refresh_view()
            return True
        # 右侧面板打开时，Esc 仅关闭面板（顺带取消瞄准）。
        if self.panel_mode in RIGHT_PANEL_MODES:
            self._sidebar_transition('world', refresh=False)
            if self.aiming:
                self.aiming = False
                self.aim_action_choice = None
                self.throw_item_index = None
                self.fire_once_index = None
                self.spray_source = None
                self._aim_assist_pos = None
                self._clear_held()
            if getattr(self, "spray_select", None) is not None:
                self.spray_select = None
                self.aim_action_choice = None
            self.refresh_view()
            return True
        # 瞄准态（发射悬停）：它不是「界面」而是持续状态，取消链原来的走法
        # 是直接放行——现在按「Esc = 返回」的语义先撤掉它，干净了才轮得到
        # 暂停菜单。⚠️ o 目标辅助**不在**此列（2026-09-20 用户拍板）：它是
        # 常开的操作偏好，Esc 不撤、也不拦开菜单。
        if self.aiming:
            # 投掷瞄准在 on_key 里已拦截（标记已处理、走不到这）；这里收的是
            # 发射悬停一类「无面板可关」的瞄准态。
            self.aiming = False
            self.aim_action_choice = None
            self.fire_once_index = None
            self.spray_source = None
            self._aim_assist_pos = None
            self._clear_held()
            self.refresh_view()
            return True
        # 教程卡是 escape 链的最底层：没有别的界面可关时，Esc = 跳过当前引导步。
        if self.session.state.tutorial.get("active") and not self.home_mode:
            message = tutorial_skip_step(self.session.state)
            if message:
                self.show_toast(message, self._player_row_screen_y())
            self.refresh_view()
            return True
        if self.home_mode:
            if self.panel_mode == "home_catalog":
                self._codex_back()
                return True
            if self.panel_mode == "home_settings":
                self._settings_back()
                return True
            if self.panel_mode == "home_newgame":
                # 开局选项页：碎片页退回调律，调律页退回存档槽页。
                self._newgame_cancel()
                return True
            if self.panel_mode == "home_saves":
                # 存档槽页：Esc 回主菜单（主页本身 Esc 才无事可做）。
                self._close_saves()
                return True
            return True  # 主页本身：Esc 无事可做（退出游戏在主页「退出」按钮）
        return False

    def _can_open_pause_menu(self) -> bool:
        """Esc 的「菜单」语义门槛：不在主页、不在结局、无任何面板/模式/动作，
        角色静止（寻路已清）——清单与用户 2026-09-20 的拍板一一对应。

        取消链（_ui_escape_chain）通常已把这些收干净；这里独立复查一遍，
        让底栏 Esc 点击（不经过 on_key）与键盘走同一条判定。
        """
        if self.home_mode or self.session.state.run_over:
            return False
        if self.panel_mode != "world":
            return False
        # o 目标辅助是常开偏好：不拦开菜单（2026-09-20 用户拍板）。
        if self.observe_mode or self.aiming:
            return False
        if self.debug_panel_open:
            return False
        if self.path or self.item_menu_target is not None or self.anomaly_detail_target is not None:
            return False
        if self.cell_detail_target is not None or self.pickup_target is not None:
            return False
        if self.insight_replace_target is not None or self.memory_replace_target is not None:
            return False
        if getattr(self, "container_index", None) is not None:
            return False
        if getattr(self, "spray_select", None) is not None:
            return False
        if getattr(self, "mirror_index", None) is not None:
            return False
        if self.lens_offer_scene:
            return False
        state = self.session.state
        if state.pending_npc_id is not None or state.pending_event_id is not None:
            return False
        if state.tutorial.get("active"):
            return False
        return True

    def action_cancel_ui(self) -> None:
        if self.layer_observation is not None:
            self._layer_key('escape')
            return
        """Esc：返回/菜单双语义——先逐层收面板/模式/动作（返回）；
        全部干净且角色静止时打开全屏暂停菜单（菜单）。"""
        if self._handled_in_on_key("escape"):
            # 这次 Esc 已被进层演出的跳过消费（on_key 先跑），不能再打开
            # 暂停菜单——跳过必须完整吞掉这个键（设计文档 §2.3）。
            return
        if self._floor_transition_skip():
            return
        if not self._ui_escape_chain():
            if self._can_open_pause_menu():
                self.open_pause_menu()
                return
            self.refresh_view()

    def _close_home_subpage(self) -> None:
        """主页子页（图鉴/设置/回忆）→ 返回主页主界面（2026-09-23 改版后 = 主菜单）。"""
        self.home_view = "menu"
        self.panel_mode = "home"
        self.refresh_view()

    def action_save_exit(self) -> None:
        if self.signal_detail_open:
            return
        """F10 / Alt+Q / 底栏按钮：保存并退出。

        游戏内保存并回主页；存档/图鉴/设置/回忆页先退回主菜单，
        主菜单上再按 F10 退出应用。
        """
        if self._active_tamper_editor() is not None:
            return
        if (self._handled_in_on_key("f10") or self._handled_in_on_key("alt+q")
                or self._handled_in_on_key("ctrl+q")):
            # 演出跳过已消费掉这次保存退出（on_key 先跑），原语义不再触发。
            return
        if self._floor_transition_skip():
            return
        if self.home_mode and self.panel_mode in ("home_catalog", "home_settings", "home_history"):
            self._close_home_subpage()
            return
        if self.home_mode:
            if self.home_view == "saves":
                self._close_saves()
            else:
                self.exit()
            return
        if not self.session.state.run_over:
            self.session.save_and_exit()
        self._return_home()

    def action_context_q(self) -> None:
        if self._active_tamper_editor() is not None:
            if getattr(self,'world_tamper_editor',None) is not None:
                self.handle_world_tamper_key('q')
            elif not self._tamper_preview_key('q'):
                self._tamper_escape(self.session.state)
            return
        if hasattr(self, '_qol_priority_q') and self._qol_priority_q():
            return
        if self.sentence_aim is not None:
            self._cancel_sentence_aim()
            self.refresh_view()
            return
        # q 是 priority 绑定，跑在 on_key 之前：失败态的瞄准也要让 q 能取消，
        # 否则它会在 on_key 之前落到别的分支（2026-10-18 玩家规则）。
        if self.aiming and getattr(self, "_aim_failed", False):
            self.cancel_aim()
            self.refresh_view()
            return
        if self.equipment_choice is not None:
            self.equipment_choice = None
            self.refresh_view()
            return
        # q 是 priority 绑定，先于 on_key 触发：覆盖面板打开时 q 只负责关闭它，
        # 否则会把当前朝向的物品投掷出去（面板还开着也照扔）。
        # 暂停菜单开着时同样先拦：priority 绑定跑在 on_key 的 pause 分支之前，
        # 不拦的话「菜单里按 q」会照着朝向把物品扔出去。
        # 进层演出同理且只能在这里拦：priority 绑定命中后按键不再转发给
        # on_key，演出中按 q 只有这条路径能碰到——当作跳过消费（§2.3）。
        if self._floor_transition_skip():
            return
        if self._cancel_attack_confirmation():
            return
        if not self.home_mode and self.panel_mode == "board_editor":
            # 联想盘编辑器：q 与 Esc 同义（先松手，再退出并丢弃草稿）。
            # priority 绑定命中后按键不再转发给 on_key，只能在这里处理。
            self.board_editor_action("cancel")
            return
        if self.tamper_editor is not None:
            # 篡改编辑：q 与 Esc 同义，逐级退（预览 → 位置 → 词表 → 收面板）。
            # 同样因为 priority 绑定先于 on_key，编辑中的 q 只有这条路径能碰到；
            # 不拦的话它会一路落到下面的投掷分支，把「按 q」变成一次真实行动。
            self._tamper_escape(self.session.state)
            return
        if self._modal_menu_open():
            return
        if self.insight_replace_target is not None:
            # 洞察替换面板：q 与 Esc 同义——先进「确定放弃替换吗？」二次确认。
            self.request_discard_insight()
            return
        if self.memory_replace_target is not None:
            # 碎片替换面板：q 与 Esc 同义。
            self.request_discard_memory()
            return
        if self.cell_detail_target is not None:
            # 格子详情优先于「结束观察」：q 只关面板，观察模式原样保留。
            self.close_cell_detail()
            return
        if self.mirror_index is not None:
            # 洞察之镜：q 与 Esc 同义——收镜不消耗。
            self.mirror_index = None
            self.refresh_view()
            return
        if getattr(self, "spray_select", None) is not None:
            # 弹药选择浮层：q 与 Esc 同义——取消选弹，不进入瞄准。
            self.spray_select = None
            self.aim_action_choice = None
            self.refresh_view()
            return
        if self.lens_offer_scene:
            # §8 S23 祭品浮层：q 与 Esc 同义——取消选择，不喂祭品。
            self._clear_lens_offer()
            self.refresh_view()
            return
        if getattr(self, "container_index", None) is not None:
            # 容器浮层：q 与 Esc 同义——收起浮层，留在行囊界面。
            self._mark_key_handled("escape")
            self.container_index = None
            self.refresh_view()
            return
        if self.aiming and self.throw_item_index is not None:
            # 瞄准中再按 q = 按当前方向投到最远（放开自由光标才走方向分支）。
            self._aim_free_cursor = None
            self.confirm_aim(direction=self.facing)
            return
        if self.observe_mode:
            # 观察模式里 q 与 Esc 同义：只结束观察，绝不投掷（世界静止时任何
            # 行动都不该落地）。这里必须先于其它分支判断，因为 priority 绑定
            # 跑在 on_key 之前，on_key 里的观察分支此时还没轮到。
            self.exit_observe()
            self.refresh_view()
            return
        if self.item_menu_target is not None:
            self.close_item_menu()
            return
        if self.anomaly_detail_target is not None:
            self.close_anomaly_detail()
            return
        if self.path:
            self.path.clear()
            self.observe_walk_path.clear()
            self.refresh_view()
            return
        if self.home_mode:
            if self.panel_mode == "home_catalog":
                self._codex_back()
            elif self.panel_mode == "home_settings":
                self._settings_back()
            elif self.panel_mode == "home_newgame":
                self._newgame_cancel()
            elif self.panel_mode == "home_saves":
                self._close_saves()
            return
        if self.panel_mode != "world" and self.panel_mode not in RIGHT_PANEL_MODES:
            return
        self.path.clear()
        self.observe_walk_path.clear()
        self.begin_throw_aim(0)
        self.refresh_view()
