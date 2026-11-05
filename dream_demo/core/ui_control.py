"""Zero-time legacy debug edits, executed only by GameSession's command owner.

The wire surface is a finite set of verbs and primitive arguments. UI selection
and rendering stay in debug_panel; no UI object or callable enters this module.
"""
from __future__ import annotations

from typing import Literal

from .content import ABILITY_DEFINITIONS, INSIGHT_DEFINITIONS, ITEM_DEFINITIONS, ANOMALY_DEFINITIONS, NPC_DEFINITIONS
from .constants import Material
from .entities import ActionResult
from ..i18n import tr
from ..materials import FLOOR_DEFINITIONS, WALL_DEFINITIONS, LIQUID_DEFINITIONS, GAS_DEFINITIONS, PORTENT_DEFINITIONS, portent_def

ControlVerb = Literal['debug_spawn', 'debug_teleport', 'debug_boost',
                      'debug_clear', 'debug_grant', 'debug_jump', 'debug_notice', 'close_dialog']


class _DebugEditor:
    def __init__(self, state):
        self.state = state
        self.debug_pending = None
        self.debug_portent_rounds = 1
        self.debug_portent_stacks = 1

    def _debug_spawn_at(self, x: int, y: int) -> bool:
        """把待释放物落到 (x, y)；位置不合法（如征兆落在空地）返回 False 不落地。"""
        if self.debug_pending is None:
            return False
        category, item = self.debug_pending
        state = self.state
        if not (0 <= x < state.width and 0 <= y < state.height):
            return False
        cell = state.cell(x, y)
        if category == "征兆":
            entity = state.entity_at(x, y)
            if entity is None:
                state.messages.append(tr("征兆只能释放在自己或意识体所在的格子。"))
                return False
            definition = portent_def(item)
            entity.portents[item] = max(1, self.debug_portent_rounds)
            if definition is not None and definition.stacks > 0:
                entity.portent_stacks[item] = max(1, self.debug_portent_stacks)
            state.messages.append(
                tr("调试：{name} 获得{portent}（{rounds} 回合）。", name=tr(entity.label), portent=tr(definition.name if definition else item), rounds=self.debug_portent_rounds)
            )
            return True
        if category == "地板":
            cell.solid = False
            cell.wall_kind = ""
            cell.liquid, cell.liquid_kind = 0, ""
            cell.gas, cell.gas_kind = 0, ""
            cell.plant = 0
            cell.floor = Material.PLAIN_AGGREGATE
            cell.aggregate_variant = item
            cell.flame = 0
        elif category in ("墙体", "固体"):
            state.configure_wall(cell, item)
        elif category == "液体":
            cell.solid = False
            cell.wall_kind = ""
            cell.liquid, cell.liquid_kind = 100, item
        elif category == "气体":
            cell.solid = False
            cell.wall_kind = ""
            cell.gas, cell.gas_kind = 100, item
        elif category == "异象":
            # 2026-09-19：同格已有意识体（异象/NPC）时拒绝放置。
            if state.entity_at(x, y) is not None:
                state.messages.append(tr("该格已有意识体，无法放置。"))
                return False
            cell.solid = False
            cell.wall_kind = ""
            state.add_defined_enemy(item, x, y)
        elif category == "其他意识体":
            if state.entity_at(x, y) is not None:
                state.messages.append(tr("该格已有意识体，无法放置。"))
                return False
            cell.solid = False
            cell.wall_kind = ""
            state._add_npc(item, x, y)
        else:  # 携带意象 / 其他物品 → 落地成掉落物
            from .entities import WorldItem

            state.world_items.append(WorldItem(state._make_item(item), x, y))
        state._material_index_ready = False
        state.messages.append(tr("调试：在 ({x}, {y}) 释放了 {item}。", x=x, y=y, item=tr(item)))
        return True

    def _debug_jump(self, item: str) -> bool:
        """「移动」扩展条目的执行体：梦中梦各层直跳 / 深层边界（28–30）。

        - **梦中梦**：从主梦跳入时补齐 ``enter_realm`` 的入场登记（归档主层、
          记入口层号与坐标、摘掉主梦修饰符）；已在梦中梦时只归档当前层再
          直跳。落层后强制 ``realm_gate_open=True``——调试直达不应被守门人
          解谜拦住。
        - **深层边界**：若在梦中梦里先摘掉 realm 身份，再走主梦的
          ``_restore_or_generate_layer``（≥28 层由它派发到结局层生成）。
        """
        state = self.state
        from ..data.dreams import realm_def

        realm_id, layer = "", 0
        if item.startswith("门之回廊·"):
            realm_id, layer = "door_corridor", int(item.rsplit("第", 1)[1].rstrip("层"))
        elif item.startswith("玩具的回忆·"):
            realm_id, layer = "toy_memories", int(item.rsplit("第", 1)[1].rstrip("层"))
        elif item.startswith("余烬廊桥·"):
            realm_id, layer = "ember_bridge", int(item.rsplit("第", 1)[1].rstrip("层"))
        elif item.startswith("退潮厅·"):
            realm_id, layer = "ebbing_hall", int(item.rsplit("第", 1)[1].rstrip("层"))
        elif item.startswith("千禧园·"):
            realm_id, layer = "millennium_garden", int(item.rsplit("第", 1)[1].rstrip("层"))
        elif item.startswith("未尽藏书宫·"):
            realm_id, layer = "library_palace", int(item.rsplit("第", 1)[1].rstrip("层"))
        elif item.startswith("至白疗所·"):
            realm_id, layer = "white_sanatorium", int(item.rsplit("第", 1)[1].rstrip("层"))
        if realm_id:
            definition = realm_def(realm_id)
            if definition is None or not 1 <= layer <= definition.layer_count:
                return False
            state._archive_active_layer()
            if not state.realm_id:
                # 从主梦跳入：登记入口（层号与坐标），日后退出照常回到这里。
                state.realm_id = realm_id
                state.entry_depth = state.depth
                state.entry_x, state.entry_y = state.player.x, state.player.y
                state._entry_layer_modifier = state.layer_modifier
                state.layer_modifier = ""
            else:
                state.realm_id = realm_id
            state.realm_depth = layer
            state._generate_realm_layer(definition, layer)
            state.realm_gate_open = True  # 调试直达：不被守门人解谜拦住
            state.messages.append(tr("调试：跳到梦中梦·{name} 第 {n} 层。",
                                     name=tr(definition.name), n=layer))
            return True
        if item.startswith("深层边界·"):
            target = int(item.rsplit("·", 1)[1])
            if state.realm_id:
                state.realm_id = ""
                state.realm_depth = 0
            state._archive_active_layer()
            state.depth = target
            state._restore_or_generate_layer(target)
            state.messages.append(tr("调试：跳到深层边界第 {n} 层。", n=target))
            return True
        return False

    def _debug_boost(self, item: str) -> bool:
        """「自我增强」执行体：前 4 项是开关（l 切换），后 3 项立即回满。

        - **全图视野**：``debug_full_vision``（视野/可见性判定在 sight.py 放开）。
        - **心智无敌**：``debug_mind_invincible``（``_lose_mind`` 统一入口直接归零）。
        - **清醒无敌/想象无限**：扣减入口太多，由 ``state._advance`` 每刻末尾
          回满——瞬时下降不累积。
        - **回满三项**：立即把对应指标拉到上限。
        """
        state = self.state
        toggles = {
            "全图视野": "debug_full_vision",
            "心智无敌": "debug_mind_invincible",
            "清醒无敌": "debug_lucidity_invincible",
            "想象无限": "debug_imagination_infinite",
        }
        if item in toggles:
            attr = toggles[item]
            value = not getattr(state, attr)
            setattr(state, attr, value)
            state.messages.append(
                tr("调试：{item}已{state}。", item=tr(item), state=tr("开启") if value else tr("关闭")))
            return True
        refill = {
            "回满心智": ("mind", "max_mind"),
            "回满清醒": ("lucidity", "max_lucidity"),
            "回满想象": ("imagination", "max_imagination"),
        }
        if item in refill:
            value_attr, cap_attr = refill[item]
            setattr(state, value_attr, getattr(state, cap_attr))
            state.messages.append(
                tr("调试：{item}（{n}）。", item=tr(item), n=getattr(state, cap_attr)))
            return True
        return False

    def _debug_teleport(self, x: int, y: int) -> bool:
        """把玩家挪到 (x, y)：只接受**空地**（界内 / 非实心 / 无其他意识体）。

        纯位移：不结算落点（液体、火焰、踩踏、落体伤害一律不触发），也不推进
        行动时间——调试瞬移只改坐标，落地之后由下一次正常行动照常处理。
        视野缓存以玩家坐标为键，位移即失效，不需要额外作废。
        """
        state = self.state
        if not (0 <= x < state.width and 0 <= y < state.height):
            state.messages.append(tr("目标格 ({x}, {y}) 在地图之外，无法传送。", x=x, y=y))
            return False
        cell = state.cell(x, y)
        if cell.solid:
            state.messages.append(tr("目标格 ({x}, {y}) 是实心的，不是空地，无法传送。", x=x, y=y))
            return False
        occupant = state.entity_at(x, y)
        if occupant is not None and occupant is not state.player:
            state.messages.append(tr("目标格 ({x}, {y}) 已有意识体，无法传送。", x=x, y=y))
            return False
        state.player.x, state.player.y = x, y
        state.messages.append(tr("调试：已传送至 ({x}, {y})。", x=x, y=y))
        return True

    def _debug_clear(self, which: int) -> None:
        state = self.state
        if which == 1:
            state.insights.clear()
            state.messages.append(tr("调试：已清空全部洞察。"))
        elif which == 2:
            state.abilities.clear()
            state.ability_cooldowns.clear()
            state.messages.append(tr("调试：已清空全部构想。"))
        elif which == 3:
            state.player.portents.clear()
            state.player.portent_stacks.clear()
            for enemy in state.enemies:
                enemy.portents.clear()
                enemy.portent_stacks.clear()
            state.messages.append(tr("调试：已清空全部征兆。"))
        elif which == 4:
            state.inventory.clear()
            state.board.clear()
            state.equipment.invalidate()
            state.hang_item_id = None
            state.messages.append(tr("调试：已清空行囊。"))



_SPAWN_TABLES = {
    "地板": FLOOR_DEFINITIONS, "墙体": WALL_DEFINITIONS, "固体": WALL_DEFINITIONS,
    "液体": LIQUID_DEFINITIONS, "气体": GAS_DEFINITIONS,
    "异象": ANOMALY_DEFINITIONS, "其他意识体": NPC_DEFINITIONS,
    "携带意象": ITEM_DEFINITIONS, "其他物品": ITEM_DEFINITIONS,
    "征兆": PORTENT_DEFINITIONS,
}


def _clear_values(state, which):
    if which == 1:
        return tuple(state.insights)
    if which == 2:
        return tuple(state.abilities), dict(state.ability_cooldowns)
    if which == 3:
        return tuple((dict(e.portents), dict(e.portent_stacks))
                     for e in [state.player, *state.enemies])
    return (tuple(state.inventory), tuple(state.board.placements),
            tuple(state.board.traces), tuple(state.board.pieces),
            state.board.focus_instance_id, state.hang_item_id)


def apply_control(state, verb: ControlVerb | None = None, *args: object) -> ActionResult:
    """Execute whitelisted controls. ``changed`` means accepted for legacy UI;
    ``state_changed`` means a gameplay value actually changed (including flags
    that the legacy save format deliberately treats as transient).
    Selection/error notices remain owner-written logs without dirtying a run.
    """
    if type(verb) is not str or any(type(value) not in (str, int, bool) for value in args):
        return ActionResult(False)
    editor = _DebugEditor(state)
    success = changed = False
    start = len(state.messages)
    if verb == 'close_dialog' and not args:
        if state.pending_npc_id is not None:
            state.close_npc_dialog()
            success = True
        else:
            before = (state.pending_event_id, state.pending_event_uid, tuple(state.events))
            state.close_event_dialog()
            success = before != (state.pending_event_id, state.pending_event_uid, tuple(state.events))
            # Removing a temporary choice also changes the saved event list.
            # Merely closing a pending dialogue remains a transient view edit.
            changed = before[2] != tuple(state.events)
        return ActionResult(success, data={'state_changed': bool(changed)})
    if verb == "debug_spawn" and len(args) == 6:
        category, item, x, y, rounds, stacks = args
        if (type(category) is not str or type(item) is not str
                or category not in _SPAWN_TABLES or item not in _SPAWN_TABLES[category]
                or any(type(v) is not int for v in (x, y, rounds, stacks))):
            return ActionResult(False)
        if not (0 <= x < state.width and 0 <= y < state.height):
            return ActionResult(False)
        editor.debug_pending = category, item
        editor.debug_portent_rounds = rounds
        editor.debug_portent_stacks = stacks
        cell = state.cell(x, y)
        fields = ("solid", "wall_kind", "liquid", "liquid_kind", "gas", "gas_kind",
                  "plant", "floor", "aggregate_variant", "flame", "creation",
                  "phase_stock", "doorway", "plant_fuel", "floor_fuel",
                  "item_burn_progress", "hardness", "height", "thickness", "integrity")
        before = tuple(getattr(cell, name) for name in fields)
        entity = state.entity_at(x, y) if category == "征兆" else None
        if entity is not None:
            before = dict(entity.portents), dict(entity.portent_stacks)
        success = editor._debug_spawn_at(x, y)
        if category == "征兆":
            changed = success and before != (dict(entity.portents), dict(entity.portent_stacks))
        elif category in ("地板", "墙体", "固体", "液体", "气体"):
            changed = success and before != tuple(getattr(cell, name) for name in fields)
        else:
            changed = success
    elif verb == "debug_teleport" and len(args) == 2 and all(type(v) is int for v in args):
        before = state.player.x, state.player.y
        success = editor._debug_teleport(*args)
        changed = success and before != (state.player.x, state.player.y)
    elif verb == "debug_boost" and len(args) == 1 and type(args[0]) is str:
        before = (state.debug_full_vision, state.debug_mind_invincible,
                  state.debug_lucidity_invincible, state.debug_imagination_infinite,
                  state.mind, state.lucidity, state.imagination)
        success = editor._debug_boost(args[0])
        changed = success and before != (state.debug_full_vision, state.debug_mind_invincible,
                  state.debug_lucidity_invincible, state.debug_imagination_infinite,
                  state.mind, state.lucidity, state.imagination)
    elif verb == "debug_clear" and len(args) == 1 and type(args[0]) is int and args[0] in (1, 2, 3, 4):
        before = _clear_values(state, args[0])
        editor._debug_clear(args[0])
        success = True
        changed = before != _clear_values(state, args[0])
    elif verb == "debug_grant" and len(args) == 2 and all(type(v) is str for v in args):
        category, item = args
        if category == "构想" and item in ABILITY_DEFINITIONS:
            changed = item not in state.abilities
            if changed:
                state.abilities.append(item)
            state.messages.append(tr("调试：直接习得构想 {name}。", name=tr(ABILITY_DEFINITIONS[item]["name"])))
            success = True
        elif category == "洞察" and item in INSIGHT_DEFINITIONS:
            before = tuple(state.insights), state.pending_insight
            state._grant_insight(item)
            changed = before != (tuple(state.insights), state.pending_insight)
            success = True
    elif verb == "debug_jump" and len(args) == 1 and type(args[0]) is str:
        # Validate the entire label before the parser/generator can mutate a layer.
        from ..data.dreams import realm_def
        prefixes = {"门之回廊": "door_corridor", "玩具的回忆": "toy_memories",
                    "余烬廊桥": "ember_bridge", "退潮厅": "ebbing_hall",
                    "千禧园": "millennium_garden", "未尽藏书宫": "library_palace",
                    "至白疗所": "white_sanatorium"}
        valid = args[0] in ("深层边界·28", "深层边界·29", "深层边界·30")
        for prefix, realm_id in prefixes.items():
            definition = realm_def(realm_id)
            if definition and args[0] in {f"{prefix}·第{n}层" for n in range(1, definition.layer_count + 1)}:
                valid = True
                break
        if valid:
            success = changed = editor._debug_jump(args[0])
    elif verb == "debug_notice" and len(args) >= 1:
        code = args[0]
        if code == "no_spawn_target" and len(args) == 1:
            state.messages.append(tr("没有可释放的目标格（移动鼠标或用观察 ? 指定）。"))
        elif code == "no_teleport_target" and len(args) == 1:
            state.messages.append(tr("没有可传送的目标格（移动鼠标或用观察 ? 指定）。"))
        elif code in ("selected_execute", "selected_spawn") and len(args) == 2 and type(args[1]) is str:
            template = "调试：已选择 {item}，按 l 执行。" if code == "selected_execute" else "调试：已选择 {item}，按 l 在光标格释放。"
            state.messages.append(tr(template, item=tr(args[1])))
        elif (code == "floor_result" and len(args) == 4 and args[1] in ("下潜", "上浮")
              and type(args[2]) is bool and type(args[3]) is str):
            state.messages.append(tr("调试：已{item}。", item=tr(args[1])) if args[2] else args[3])
    # Debug changes may alter sight inputs without advancing an action/frame.
    if changed:
        state._sight_radius_cache = None
        from .vision.cache import invalidate
        invalidate(state)
    message = state.messages[-1] if len(state.messages) > start else ""
    return ActionResult(bool(success), message, {"state_changed": bool(changed)})
