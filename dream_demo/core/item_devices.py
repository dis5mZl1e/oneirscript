"""部署类物品的运行期装置（2026-10-22 A2 P4/P5 新增十件）。

十件新物品里有八件不是「用完即走」的消耗品，而是**留在场上**的装置：夜班灯、
折叠虹吸管、应急蜡封、拆迁线轴、折好的逃生通道、未寄出的雷暴、最后一圈安静、
瓶装天亮。它们各自按回合结算（发声／搬料／化蜡／割墙／放电／放油），而且结算
一律走既有的真实管线——声波走 ``core/acoustics.py``，放电走
``core/materials_sim.py`` 的导电区，燃烧走 ``_ignite_cell``，蜡墙走
``core/phase_changes.py``。装置不给玩家另开一套规则。

装置记录挂在 ``state.realm_features['item_devices']``：逐层存放，回到本层仍在，
换层即清空（与其它逐层陈设同口径），也随层快照存档（记录全是可序列化的
dict／标量）。每回合由 ``core.state._advance`` 调一次 :func:`tick`。

落点合法性只读 ``core/item_targeting.py``；取消瞄准或非法提交一律不消耗物品、
不留装置、不花行动。
"""

from __future__ import annotations

from typing import Any

from ..i18n import tr
from ..materials.plants import plant_survives_liquid
from . import phase_changes
from .item_targeting import protected_cell, seals_only_path

# ---- 夜班灯 ----
BEACON_TURNS = 10
BEACON_LIGHT_RADIUS = 3
BEACON_SOUND_RADIUS = 12
# 落地那一声之外，第 3／6／9 回合各再咳一次。
BEACON_SOUND_OFFSETS = (3, 6, 9)

# ---- 折叠虹吸管 ----
SIPHON_TURNS = 8
SIPHON_LIQUID_PER_TURN = 8
SIPHON_LIQUID_TOTAL = 64
SIPHON_GAS_PER_TURN = 4
SIPHON_GAS_TOTAL = 32

# ---- 应急蜡封 ----
WAX_SEAL_TURNS = 10
WAX_SEAL_AMOUNT = 20
WAX_SEAL_INTEGRITY = 60
WAX_SEAL_WALL = "蜡化记忆墙"
WAX_SEAL_LIQUID = "熔融蜡烛"

# ---- 拆迁线轴 ----
SPOOL_TURNS = 3
SPOOL_RANGE = 6
SPOOL_TARGETS = 3
SPOOL_TOTAL = 180
SPOOL_PER_TURN = 60

# ---- 折好的逃生通道 ----
ESCAPE_TURNS = 8
ESCAPE_USES = 3

# ---- 未寄出的雷暴 ----
STORM_TURNS = 4
STORM_LIQUID_PER_TURN = 15
STORM_LIQUID_TOTAL = 60
STORM_GAS_PER_TURN = 10
STORM_GAS_TOTAL = 40
STORM_DISCHARGE_POWER = 2

# ---- 最后一圈安静 ----
QUIET_TURNS = 6
QUIET_RADIUS = 4

# ---- 瓶装天亮 ----
SUNRISE_FUSE_TURNS = 2
SUNRISE_BURN_TURNS = 3
SUNRISE_FUEL_TOTAL = 80
SUNRISE_FUEL_PER_TURN = 27
SUNRISE_RADIUS = 3
SUNRISE_IGNITE_STRENGTH = 4


# ---------------------------------------------------------------------------
# 装置登记
# ---------------------------------------------------------------------------

def devices(state) -> list[dict]:
    """本层的全部装置记录。"""
    features = getattr(state, "realm_features", None)
    if not isinstance(features, dict):
        return []
    records = features.get("item_devices")
    return records if isinstance(records, list) else []


def _register(state, kind: str, x: int, y: int, turns: int, **data) -> dict:
    features = getattr(state, "realm_features", None)
    if not isinstance(features, dict):
        return {}
    records = features.setdefault("item_devices", [])
    if not isinstance(records, list):
        records = []
        features["item_devices"] = records
    record = {"kind": kind, "x": int(x), "y": int(y),
              "turns": int(turns), "data": dict(data)}
    records.append(record)
    return record


def _drop(state, record: dict) -> None:
    records = devices(state)
    if record in records:
        records.remove(record)
    features = getattr(state, "realm_features", None)
    if isinstance(features, dict) and not features.get("item_devices"):
        features.pop("item_devices", None)


def register_device(state, kind: str, x: int, y: int, turns: int, **data) -> dict:
    """公开登记入口：扩展包装备的装置与旧十件共用同一张逐层表。"""
    return _register(state, kind, x, y, turns, **data)


# ---------------------------------------------------------------------------
# 材料投放（不与异种材料混装，装不下就顺到四邻）
# ---------------------------------------------------------------------------

def _deposit(state, x: int, y: int, kind: str, amount: int, attribute: str) -> int:
    """把 ``amount`` 单位材料放进 (x, y)；放不下就顺到四邻。返回实际放入量。"""
    if amount <= 0:
        return 0
    cell = state.cell(x, y)
    current = int(getattr(cell, attribute))
    current_kind = str(getattr(cell, attribute + "_kind", "") or "")
    if not cell.solid and (current == 0 or current_kind == kind):
        take = min(amount, max(0, 100 - current))
        if take > 0:
            setattr(cell, attribute, current + take)
            setattr(cell, attribute + "_kind", kind)
            if attribute == "liquid" and cell.plant and not plant_survives_liquid(cell.plant):
                state.set_plant_at(cell, 0)
            state._sync_material_position(x, y)
            return take
    rest = amount
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if rest <= 0:
            break
        if not (0 <= nx < state.width and 0 <= ny < state.height):
            continue
        neighbor = state.cell(nx, ny)
        if neighbor.solid:
            continue
        ncurrent = int(getattr(neighbor, attribute))
        nkind = str(getattr(neighbor, attribute + "_kind", "") or "")
        if ncurrent and nkind != kind:
            continue
        take = min(rest, max(0, 100 - ncurrent))
        if take <= 0:
            continue
        setattr(neighbor, attribute, ncurrent + take)
        setattr(neighbor, attribute + "_kind", kind)
        if attribute == "liquid" and neighbor.plant and not plant_survives_liquid(neighbor.plant):
            state.set_plant_at(neighbor, 0)
        state._sync_material_position(nx, ny)
        rest -= take
    return amount - rest


def _transfer(state, source_pos, exit_pos, amount: int, attribute: str) -> int:
    """从源格搬到出口格；出口装不下或异种材料时**不动**（不吞材料）。"""
    sx, sy = source_pos
    ex, ey = exit_pos
    source = state.cell(sx, sy)
    exit_cell = state.cell(ex, ey)
    held = int(getattr(source, attribute))
    kind = str(getattr(source, attribute + "_kind", "") or "")
    if held <= 0 or not kind:
        return 0
    current = int(getattr(exit_cell, attribute))
    current_kind = str(getattr(exit_cell, attribute + "_kind", "") or "")
    if current and current_kind != kind:
        return 0
    take = min(amount, held, max(0, 100 - current))
    if take <= 0:
        return 0
    setattr(source, attribute, held - take)
    if held - take <= 0:
        setattr(source, attribute, 0)
        setattr(source, attribute + "_kind", "")
    setattr(exit_cell, attribute, current + take)
    setattr(exit_cell, attribute + "_kind", kind)
    if attribute == "liquid":
        if source.plant and not plant_survives_liquid(source.plant):
            state.set_plant_at(source, 0)
        if exit_cell.plant and not plant_survives_liquid(exit_cell.plant):
            state.set_plant_at(exit_cell, 0)
    state._sync_material_position(sx, sy)
    state._sync_material_position(ex, ey)
    return take


# ---------------------------------------------------------------------------
# 部署入口
# ---------------------------------------------------------------------------

def deploy_beacon(state, x: int, y: int) -> tuple[bool, str, dict]:
    """误点的夜班灯：一盏弱光＋定时咳声。"""
    cell = state.cell(x, y)
    if cell.solid:
        return False, tr("那里立着东西，灯放不上去。"), {}
    data = {"prev_light_radius": int(cell.light_radius),
            "prev_light_on": bool(cell.light_on),
            "elapsed": 0, "sounds": list(BEACON_SOUND_OFFSETS)}
    cell.light_radius = BEACON_LIGHT_RADIUS
    cell.light_on = True
    _register(state, "beacon", x, y, BEACON_TURNS, **data)
    state._sound_pulse(x, y, BEACON_SOUND_RADIUS, by_player=True, full_alert=True,
                       category="lure", source=tr("误点的夜班灯"))
    state.messages.append(tr("夜班灯亮着，咳了一声——那声音够远。"))
    return True, tr("夜班灯落在地上，灯芯一直亮着。"), {}


def deploy_siphon(state, source_pos, exit_pos) -> tuple[bool, str, dict]:
    """折叠虹吸管：架在源与出口之间，每回合搬一点。"""
    sx, sy = source_pos
    ex, ey = exit_pos
    source = state.cell(sx, sy)
    if source.liquid > 0:
        mode, total = "liquid", SIPHON_LIQUID_TOTAL
        per_turn = SIPHON_LIQUID_PER_TURN
    elif source.gas > 0:
        mode, total = "gas", SIPHON_GAS_TOTAL
        per_turn = SIPHON_GAS_PER_TURN
    else:
        return False, tr("源格里什么也没有可搬的东西。"), {}
    _register(state, "siphon", sx, sy, SIPHON_TURNS,
              source=(sx, sy), exit=(ex, ey), mode=mode,
              per_turn=per_turn, left=total)
    state.messages.append(
        tr("虹吸管架好了——它每回合替你搬一点（{mode}）。",
           mode=tr("液体") if mode == "liquid" else tr("气体")))
    return True, tr("折叠虹吸管展开，架在源与出口之间。"), {}


def deploy_wax_seal(state, x: int, y: int) -> tuple[bool, str, dict]:
    """应急蜡封：挤成一堵蜡墙，10 回合后化回等量熔蜡。"""
    cell = state.cell(x, y)
    if cell.solid:
        return False, tr("那里已经立着东西了。"), {}
    if seals_only_path(state, x, y):
        return False, tr("封住这里就断了唯一的路——换个地方。"), {}
    base_floor = cell.aggregate_variant
    state.configure_wall(cell, WAX_SEAL_WALL)
    cell.integrity = WAX_SEAL_INTEGRITY
    cell.phase_stock = {"form": "wall", "kind": WAX_SEAL_LIQUID,
                        "amount": WAX_SEAL_AMOUNT, "initial_amount": WAX_SEAL_AMOUNT,
                        "initial_integrity": WAX_SEAL_INTEGRITY,
                        "wall": WAX_SEAL_WALL, "base_floor": base_floor}
    state._material_index_ready = False
    _register(state, "wax_seal", x, y, WAX_SEAL_TURNS)
    state.messages.append(tr("蜡从管口挤出来，堆成了一堵墙（完整度 {n}）。",
                             n=WAX_SEAL_INTEGRITY))
    return True, tr("应急蜡封挤成了一堵蜡墙。"), {}


def deploy_spool(state, direction) -> tuple[bool, str, dict]:
    """拆迁用的线轴：朝一个方向抽线，割开沿途挡路的东西。"""
    dx, dy = int(direction[0]), int(direction[1])
    if not (dx or dy):
        return False, tr("没有方向，线抽不出去。"), {}
    targets: list[tuple[int, int]] = []
    for step in range(1, SPOOL_RANGE + 1):
        tx = state.player.x + dx * step
        ty = state.player.y + dy * step
        if not state.inside_board(tx, ty):
            break
        cell = state.cell(tx, ty)
        if not cell.solid:
            continue
        if protected_cell(state, tx, ty):
            continue
        targets.append((tx, ty))
        if len(targets) >= SPOOL_TARGETS:
            break
    if not targets:
        return False, tr("那个方向没有能割开的东西。"), {}
    _register(state, "spool", state.player.x, state.player.y, SPOOL_TURNS,
              targets=targets, left=SPOOL_TOTAL)
    state.messages.append(tr("细线绷紧，咬住了 {n} 处挡路的东西。", n=len(targets)))
    return True, tr("线抽了出去，绷在那几处障碍上。"), {}


def deploy_escape_route(state, first, second) -> tuple[bool, str, dict]:
    """折好的逃生通道：接在两个空位之间，只够走三趟。"""
    ax, ay = first
    bx, by = second
    _register(state, "escape", ax, ay, ESCAPE_TURNS,
              a=(ax, ay), b=(bx, by), uses=0)
    state.messages.append(tr("两条折好的路接上了——走过去比绕远路近。"))
    return True, tr("折好的逃生通道铺开了。"), {}


def deploy_quiet_boundary(state) -> tuple[bool, str, dict]:
    """最后一圈安静：一圈临时声衰减区。"""
    _register(state, "quiet", state.player.x, state.player.y, QUIET_TURNS)
    state.messages.append(tr("一圈安静罩住你——穿过它的声音会再哑一分。"))
    return True, tr("最后一圈安静铺开了。"), {}


# ---------------------------------------------------------------------------
# 投掷落点（winter_sample / storm_accumulator / bottled_sunrise）
# ---------------------------------------------------------------------------

def winter_sample_landing(state, x: int, y: int, power: int) -> tuple[str, dict]:
    """冬天的样本：中心 8、四邻各 4 单位液氮。"""
    total = max(0, int(power or 24))
    center = 8
    neighbor = 4
    frozen = 0
    for tx, ty, amount in ((x, y, center), (x + 1, y, neighbor), (x - 1, y, neighbor),
                           (x, y + 1, neighbor), (x, y - 1, neighbor)):
        if not (0 <= tx < state.width and 0 <= ty < state.height):
            continue
        if state.cell(tx, ty).solid:
            continue
        frozen += _deposit(state, tx, ty, "液氮", amount, "liquid")
    state.messages.append(tr("薄壁瓶碎了，白雾漫开（放出 {n} 单位液氮）。", n=frozen))
    return tr("冬天的样本碎开，白雾漫开。"), {"frozen": frozen, "total": total}


def storm_accumulator_landing(state, x: int, y: int) -> tuple[str, dict]:
    """未寄出的雷暴：落地后分四回合倒出电荷，最后放一次电。"""
    _register(state, "storm", x, y, STORM_TURNS,
              liquid_left=STORM_LIQUID_TOTAL, gas_left=STORM_GAS_TOTAL)
    state.messages.append(tr("雷暴信落地，封口还在慢慢渗出电荷。"))
    return tr("未寄出的雷暴落在地上，开始渗出电荷。"), {}


def bottled_sunrise_landing(state, x: int, y: int) -> tuple[str, dict]:
    """瓶装天亮：两回合引信，然后三回合放油点火。"""
    _register(state, "sunrise", x, y, SUNRISE_FUSE_TURNS, phase="fuse")
    state.messages.append(tr("瓶口的引信亮了起来——还有两回合。"))
    return tr("瓶装天亮落在地上，引信亮着。"), {}


# ---------------------------------------------------------------------------
# 每回合结算
# ---------------------------------------------------------------------------

def tick(state) -> None:
    """推进本层全部装置；由 ``core.state._advance`` 每回合调用一次。"""
    from ..equipment import gear_tools

    gear_tools.tick_state(state)
    records = devices(state)
    if not records:
        return
    alive: list[dict] = []
    for record in list(records):
        handler = _HANDLERS.get(str(record.get("kind", "")))
        if handler is None:
            from . import expansion_consumables
            keep = expansion_consumables.tick_record(state, record)
            if keep is not None:
                if keep:
                    alive.append(record)
                continue
            keep = gear_tools.tick_record(state, record)
            if keep:
                alive.append(record)
            continue
        if handler(state, record):
            alive.append(record)
    features = getattr(state, "realm_features", None)
    if isinstance(features, dict):
        features["item_devices"] = alive


def _restore_light(state, record: dict) -> None:
    cell = state.cell(record["x"], record["y"])
    data = record.get("data", {})
    cell.light_radius = int(data.get("prev_light_radius", 0))
    cell.light_on = bool(data.get("prev_light_on", True))


def _tick_beacon(state, record: dict) -> bool:
    x, y = record["x"], record["y"]
    cell = state.cell(x, y)
    if cell.flame > 0:
        _restore_light(state, record)
        state.messages.append(tr("夜班灯被火吞了——那点光灭了。"))
        return False
    record["turns"] = int(record.get("turns", 0)) - 1
    data = record.setdefault("data", {})
    data["elapsed"] = int(data.get("elapsed", 0)) + 1
    if data["elapsed"] in [int(value) for value in data.get("sounds", ())]:
        state._sound_pulse(x, y, BEACON_SOUND_RADIUS, by_player=True, full_alert=True,
                           category="lure", source=tr("误点的夜班灯"))
        state.messages.append(tr("夜班灯又咳了一声——声音还在原处。"))
    if int(record.get("turns", 0)) <= 0:
        _restore_light(state, record)
        state.messages.append(tr("灯芯烧到尽头，夜班灯熄了。"))
        return False
    return True


def _tick_siphon(state, record: dict) -> bool:
    data = record.setdefault("data", {})
    mode = str(data.get("mode", "liquid"))
    attribute = "liquid" if mode == "liquid" else "gas"
    per_turn = int(data.get("per_turn", SIPHON_LIQUID_PER_TURN))
    left = int(data.get("left", 0))
    moved = _transfer(state, data.get("source", (0, 0)), data.get("exit", (0, 0)),
                      min(per_turn, left), attribute)
    data["left"] = max(0, left - moved)
    record["turns"] = int(record.get("turns", 0)) - 1
    if moved <= 0:
        state.messages.append(tr("管子停转了——源干了，或者出口已经满了。"))
        return False
    if int(record.get("turns", 0)) <= 0:
        state.messages.append(tr("虹吸管灌满了，撤了下来。"))
        return False
    return True


def _tick_wax_seal(state, record: dict) -> bool:
    x, y = record["x"], record["y"]
    cell = state.cell(x, y)
    if not cell.solid or cell.wall_kind != WAX_SEAL_WALL:
        return False
    record["turns"] = int(record.get("turns", 0)) - 1
    if int(record.get("turns", 0)) > 0:
        return True
    # 10 回合到点：按存量逐步化回熔蜡（每回合化一批，受热提前融化走热路径）。
    melted = phase_changes.melt_wall(state, x, y, force=True)
    if not cell.solid or cell.wall_kind != WAX_SEAL_WALL:
        state.messages.append(tr("蜡墙化完了——地上留下一摊熔蜡。"))
        return False
    if not melted:
        state.messages.append(tr("蜡墙化不动了——四周已经没有能放蜡的地方。"))
        return False
    return True


def _tick_spool(state, record: dict) -> bool:
    data = record.setdefault("data", {})
    budget = min(SPOOL_PER_TURN, int(data.get("left", 0)))
    for tx, ty in list(data.get("targets", ())):
        if budget <= 0:
            break
        cell = state.cell(tx, ty)
        if not cell.solid:
            continue
        take = min(budget, int(cell.integrity))
        cell.integrity -= take
        budget -= take
        data["left"] = max(0, int(data.get("left", 0)) - take)
        if cell.integrity <= 0:
            state.destroy_wall(tx, ty, "spool")
    record["turns"] = int(record.get("turns", 0)) - 1
    if int(record.get("turns", 0)) <= 0 or int(data.get("left", 0)) <= 0:
        state.messages.append(tr("线抽完了，绷紧的细线松了。"))
        return False
    return True


def _tick_escape(state, record: dict) -> bool:
    record["turns"] = int(record.get("turns", 0)) - 1
    if int(record.get("turns", 0)) <= 0:
        state.messages.append(tr("折好的通道松开了。"))
        return False
    return True


def _discharge_storm(state, x: int, y: int) -> None:
    zone = state._conductive_zone((x, y))
    if not zone:
        state.messages.append(tr("雷暴在绝缘的地面上散了——没能放出电弧。"))
        return
    struck = 0
    for enemy in state.enemies:
        if enemy.integrity <= 0:
            continue
        if (enemy.x, enemy.y) not in zone or enemy.relation == "稳定意识":
            continue
        state._kill_full_reward = True
        _damage_number_before = enemy.integrity
        enemy.integrity = max(0, enemy.integrity - STORM_DISCHARGE_POWER)
        from .hit_events import note_integrity_loss
        note_integrity_loss(state, enemy, _damage_number_before)
        state._apply_direct_portent(enemy, "shocked", 2)
        struck += 1
        if enemy.integrity <= 0:
            state._resolve_enemy(enemy)
    state.messages.append(tr("雷暴放电，电弧顺着导电的记忆液窜过去（{n} 个失控意识挨了这一记）。",
                             n=struck))
    state._charge_electric_field(zone, source="battery", origin=(x, y))
    state._emit_combat_fx("electric", (x, y), zone)


def _tick_storm(state, record: dict) -> bool:
    x, y = record["x"], record["y"]
    data = record.setdefault("data", {})
    record["turns"] = int(record.get("turns", 0)) - 1
    liquid_left = int(data.get("liquid_left", 0))
    if liquid_left > 0:
        amount = min(STORM_LIQUID_PER_TURN, liquid_left)
        _deposit(state, x, y, "导电液态记忆", amount, "liquid")
        data["liquid_left"] = liquid_left - amount
    gas_left = int(data.get("gas_left", 0))
    if gas_left > 0:
        amount = min(STORM_GAS_PER_TURN, gas_left)
        _deposit(state, x, y, "静电尘", amount, "gas")
        data["gas_left"] = gas_left - amount
    if int(record.get("turns", 0)) <= 0:
        _discharge_storm(state, x, y)
        return False
    return True


def _tick_quiet(state, record: dict) -> bool:
    record["turns"] = int(record.get("turns", 0)) - 1
    if int(record.get("turns", 0)) <= 0:
        state.messages.append(tr("最后一圈安静散了。"))
        return False
    return True


def _sunrise_cells(state, x: int, y: int) -> list[tuple[int, int]]:
    """落点周围视线可达、半径 3 的格子。"""
    cells: list[tuple[int, int]] = []
    for ty in range(y - SUNRISE_RADIUS, y + SUNRISE_RADIUS + 1):
        for tx in range(x - SUNRISE_RADIUS, x + SUNRISE_RADIUS + 1):
            if not state.inside_board(tx, ty):
                continue
            if max(abs(tx - x), abs(ty - y)) > SUNRISE_RADIUS:
                continue
            if (tx, ty) != (x, y) and not state._has_line_of_sight(x, y, tx, ty):
                continue
            if state.cell(tx, ty).solid:
                continue
            cells.append((tx, ty))
    return cells


def _tick_sunrise(state, record: dict) -> bool:
    x, y = record["x"], record["y"]
    data = record.setdefault("data", {})
    record["turns"] = int(record.get("turns", 0)) - 1
    if str(data.get("phase", "fuse")) == "fuse":
        if int(record.get("turns", 0)) > 0:
            return True
        data["phase"] = "burn"
        record["turns"] = SUNRISE_BURN_TURNS
        state.messages.append(tr("瓶口炸开——天亮开始往外倒。"))
    fuel_left = int(data.get("fuel_left", SUNRISE_FUEL_TOTAL))
    amount = min(SUNRISE_FUEL_PER_TURN, fuel_left)
    data["fuel_left"] = max(0, fuel_left - amount)
    cells = _sunrise_cells(state, x, y)
    if cells:
        # 按格均分：先整除，余数补给前几格，预算花完就停。
        # 旧写法 `share = max(1, amount // len(cells))` 在「格数 > 预算」时每格
        # 强发 1 单位：半径 3 是 7×7＝49 格，每回合 27 的预算被摊成 49，
        # 三回合实发 49＋49＋26＝124，与方案的「总计 80 单位燃油」不符
        # （2026-10-22 D4 验收实测发现并修正）。现在总量严格等于 80。
        share, extra = divmod(amount, len(cells))
        for index, (tx, ty) in enumerate(cells):
            give = share + (1 if index < extra else 0)
            if give <= 0:
                break
            _deposit(state, tx, ty, "燃油", give, "liquid")
            amount -= give
    if int(record.get("turns", 0)) > 0:
        return True
    ignited = 0
    burning: list[tuple[int, int]] = []
    for tx, ty in _sunrise_cells(state, x, y):
        if state._ignite_cell(tx, ty, SUNRISE_IGNITE_STRENGTH, by_player=True):
            ignited += 1
            burning.append((tx, ty))
    state._emit_combat_fx("fire", (x, y), burning)
    state.messages.append(tr("天亮烧了起来（点燃 {n} 格）。", n=ignited))
    return False


_HANDLERS = {
    "beacon": _tick_beacon,
    "siphon": _tick_siphon,
    "wax_seal": _tick_wax_seal,
    "spool": _tick_spool,
    "escape": _tick_escape,
    "storm": _tick_storm,
    "quiet": _tick_quiet,
    "sunrise": _tick_sunrise,
}


# ---------------------------------------------------------------------------
# 静音圈（供 core/acoustics.py 读取）与逃生通道（供移动动作读取）
# ---------------------------------------------------------------------------

def quiet_zones(state) -> list[tuple[int, int, int]]:
    """当前生效的静音圈：(中心 x, 中心 y, 半径)。

    中心取**放置时**记下的那一格，不跟着人走——方案 §6 的定位是「放置半径 4
    的临时声衰减区」：把圈子留在身后撤，穿越边界的声才额外衰减；跟着人走
    就变成了随身消音，不是同一件东西。
    """
    zones: list[tuple[int, int, int]] = []
    for record in devices(state):
        if str(record.get("kind", "")) != "quiet":
            continue
        if int(record.get("turns", 0)) <= 0:
            continue
        zones.append((int(record["x"]), int(record["y"]), QUIET_RADIUS))
    return zones


def try_escape(state, position) -> tuple[int, int] | None:
    """玩家踏到折好通道的一端 → 送到另一端；返回落点或 None。"""
    for record in devices(state):
        if str(record.get("kind", "")) != "escape":
            continue
        data = record.get("data", {})
        first = tuple(data.get("a", ()))
        second = tuple(data.get("b", ()))
        if position == first:
            destination = second
        elif position == second:
            destination = first
        else:
            continue
        if len(destination) != 2:
            continue
        used = int(data.get("uses", 0))
        if used >= ESCAPE_USES:
            continue
        dx, dy = int(destination[0]), int(destination[1])
        if not state.inside_board(dx, dy):
            continue
        cell = state.cell(dx, dy)
        if cell.solid or state.entity_at(dx, dy) is not None:
            continue
        data["uses"] = used + 1
        state.messages.append(tr("折好的通道把你送到了另一头（还剩 {n} 趟）。",
                                n=ESCAPE_USES - used - 1))
        return (dx, dy)
    return None


def escape_uses_left(state) -> int:
    """当前层折好通道还剩几趟（供面板提示）。"""
    left = 0
    for record in devices(state):
        if str(record.get("kind", "")) == "escape":
            data = record.get("data", {})
            left += max(0, ESCAPE_USES - int(data.get("uses", 0)))
    return left
