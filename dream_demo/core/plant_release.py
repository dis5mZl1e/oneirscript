"""「被破坏那一下」的植物释出管线与常驻周期效果（docs 2026-10-26 §3.4）。

两类效果都写在这里，因为它们的口径必须一致：**只作用于真实地形与真实格**，
不伪造材料、不凭空扩大范围、不在 UI 上改数字假装生效。

一、一次性释出 :func:`apply_plant_release`
    踩踏（真实进入并被压碎）与拔除（脚下拔或篡改选格）共用这条入口，执行
    顺序固定为 **移除本株 → 液体 → 搬气 → 气体 → 点火 → 放电 → 发声 →
    削耐久 → 挂征兆**。顺序不是风格问题，三处顺序错会静默失败：

    - 先点火后倒油：``_ignite_cell`` 的 ``_cell_is_flammable`` 判的是一块
      还没油的地板；
    - 先释液不移除植株：``_add_liquid`` 会走「液面漫过即淹死植物」，让
      「这株是否 immune_liquid」决定它算不算被破坏过；
    - 导电株不同步登记：``electric_field_cells`` 每帧把记账格滤空，看起来
      放了电、实际零格结算。

    一次性预算由 ``cell.plant_state['released']`` 记账：踩完再拔不会拿两份。

二、常驻周期 :func:`tick_periodic_plants`
    吸收／搬气／净化按真实世界回合推进，预算存在格子里（``plant_state``），
    耗尽不因离开、重进、读档、催生恢复。没有可作用的目标就不扣预算。
"""

from __future__ import annotations

from typing import Any

from ..i18n import get_language, tr
from ..materials.liquids import LIQUID_DEFINITIONS
from ..materials.gases import GAS_DEFINITIONS
from ..materials.plants import plant_def_for, plant_budget_key

# 常驻效果只在这些格上发生：源株本格与它的四邻（气体/液体吸收的取料半径）。
_RING4 = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))
_NEIGHBORS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def plant_direction(state: Any, x: int, y: int) -> tuple[int, int]:
    """这株的朝向（压差囊的嘴、风向标苔的风向）。

    生成时登记在 ``plant_state['direction']``；旧存档/程序化摆放没有登记时
    用坐标推导一个**稳定**朝向——不能每次读都掷骰子，否则搬气方向会跳。
    """
    cell = state.cell(x, y)
    key = (cell.plant_state or {}).get("direction")
    if isinstance(key, (list, tuple)) and len(key) == 2:
        return int(key[0]), int(key[1])
    if isinstance(key, str):
        table = {"n": (0, -1), "e": (1, 0), "s": (0, 1), "w": (-1, 0)}
        if key in table:
            return table[key]
    return _NEIGHBORS4[(x * 7 + y * 13) % 4]


def ring_cells(state: Any, x: int, y: int, *, radius: int = 1) -> list[tuple[int, int]]:
    """源格 + R1 一圈，按固定顺序（本格优先，其余按 (y,x) 排序）。

    斜角邻格若被两侧墙完全夹死（两个正交邻格都是实心）则排除——不是隔墙
    光环，也不越层。坐标越界直接丢弃。
    """
    result = [(x, y)]
    others: list[tuple[int, int]] = []
    for ny in range(y - radius, y + radius + 1):
        for nx in range(x - radius, x + radius + 1):
            if (nx, ny) == (x, y):
                continue
            if not (0 <= nx < state.width and 0 <= ny < state.height):
                continue
            if radius == 1 and nx != x and ny != y:
                # 斜角：两个正交邻格都实心 → 夹死，够不到。
                if state.cell(nx, y).solid and state.cell(x, ny).solid:
                    continue
            others.append((nx, ny))
    others.sort(key=lambda pos: (pos[1], pos[0]))
    result.extend(others)
    return result


def _deposit_material(state: Any, targets: list[tuple[int, int]], kind: str,
                      amount: int, *, sink: list | None = None) -> int:
    """把 ``amount`` 单位材料摊到若干格，返回实际落地的总量。

    ``sink`` 收到的是**真正落了材料**的格（不是候选格），供释出反应按真实
    作用格作画；不传则只算总量，行为与旧代码完全一致。
    """
    if amount <= 0 or not kind:
        return 0
    if kind in GAS_DEFINITIONS:
        capacity = lambda cell: 100 - cell.gas  # noqa: E731
    elif kind in LIQUID_DEFINITIONS:
        capacity = lambda cell: 100 - cell.liquid  # noqa: E731
    else:
        return 0
    accepted: list[tuple[int, int]] = []
    for nx, ny in targets:
        cell = state.cell(nx, ny)
        if cell.solid or capacity(cell) <= 0:
            continue
        if kind in LIQUID_DEFINITIONS and cell.liquid_kind:
            from .tamper_protection import liquid_reason
            if liquid_reason(cell.liquid_kind):
                # 任务保护液体格：不往里倒，也不替玩家把任务废掉。
                continue
        accepted.append((nx, ny))
        if len(accepted) >= 3:
            break
    if not accepted:
        return 0
    share, remainder = divmod(int(amount), len(accepted))
    landed = 0
    for index, (nx, ny) in enumerate(accepted):
        part = share + (1 if index < remainder else 0)
        if part <= 0:
            continue
        cell = state.cell(nx, ny)
        if kind in GAS_DEFINITIONS:
            state._add_gas(cell, kind, part)
        else:
            state._add_liquid(cell, kind, part)
        landed += part
        if sink is not None:
            sink.append((nx, ny))
    return landed


def _push_gas(state: Any, x: int, y: int, amount: int,
              *, sink: list | None = None) -> int:
    """把本格已有的同种气体按朝向推向邻格，返回实际搬运量。"""
    cell = state.cell(x, y)
    if cell.gas <= 0 or cell.gas_kind not in GAS_DEFINITIONS or amount <= 0:
        return 0
    dx, dy = plant_direction(state, x, y)
    nx, ny = x + dx, y + dy
    if not (0 <= nx < state.width and 0 <= ny < state.height):
        return 0
    target = state.cell(nx, ny)
    if target.solid or target.gas >= 100:
        return 0
    moved = min(int(amount), int(cell.gas), 100 - int(target.gas))
    if moved <= 0:
        return 0
    kind = cell.gas_kind
    cell.gas = max(0, cell.gas - moved)
    if cell.gas == 0:
        cell.gas_kind = ""
    state._add_gas(target, kind, moved)
    state._material_index_ready = False
    if sink is not None:
        sink.append((nx, ny))
    return moved


def _apply_integrity(state: Any, targets: list[tuple[int, int]], loss: int,
                     *, sink: list | None = None) -> int:
    """只削不碎、下限 1、不给崩解度、不产碎片，跳过受保护地形。"""
    if loss <= 0:
        return 0
    from .tamper_protection import terrain_reason
    hit = 0
    for nx, ny in targets:
        if hit >= 3:
            break
        cell = state.cell(nx, ny)
        if not cell.solid or cell.integrity <= 1:
            continue
        if terrain_reason(state, nx, ny):
            continue
        cell.integrity = max(1, int(cell.integrity) - int(loss))
        hit += 1
        if sink is not None:
            sink.append((nx, ny))
    if hit:
        state._sight_revision = int(getattr(state, "_sight_revision", 0)) + 1
    return hit


def _grant_portent(state: Any, holder: Any, portent_id: str) -> bool:
    """挂一次征兆；已经带着同一条就不重复刷新（禁止来回踩把目标钉死）。"""
    if holder is None or not portent_id:
        return False
    if holder.portents.get(portent_id):
        return False
    return bool(state._grant_portent_direct(holder, portent_id))


def apply_plant_release(state: Any, holder: Any, x: int, y: int, code: int,
                        trigger: str, *, removal_code: int = 0,
                        announce: bool = True) -> dict:
    """执行一次植物释出，返回各通道的实际结果（空 dict = 什么都没做）。

    ``trigger`` 只接受 ``"trample"`` / ``"uproot"``；``removal_code`` 是踩踏后
    该格应留下的植物码（0 = 拔掉，或 ``trample_to`` 的变体）。植株在释出
    **之前**就被移除/替换，所有材料都落在真实的地形上。
    """
    definition = plant_def_for(code) if code else None
    release = definition.release if definition is not None else None
    if release is None or not release.allows(trigger):
        return {}
    cell = state.cell(x, y)
    if cell.plant != code:
        # 这一格已经不是它了（例如被液体提前冲走）：不释出，也不报成功。
        return {}
    state_of_cell = cell.plant_state
    if not isinstance(state_of_cell, dict):
        state_of_cell = {}
        cell.plant_state = state_of_cell
    if state_of_cell.get("released"):
        return {}

    # 1) 一次性预算先落账，再动地形——中途任何一步失败都不会变成「还能再释一次」。
    state_of_cell["released"] = 1
    # 2) 移除本株（踩踏可能只是压成倒伏态）。
    state.set_plant_at(cell, int(removal_code) if trigger == "trample" else 0)
    cell = state.cell(x, y)
    if cell.plant:
        # 变体留在原地时，把一次性标记写在**活着的那一格**上：``set_plant_at``
        # 换种会清空 plant_state，旧字典已经没人看了。
        #
        # 整株被拔走/踩碎（plant == 0）就不再记账：那一格已经没有任何株可
        # 释出，将来重新长出来的也是**另一株**，凭 ``cell.plant != code`` 就
        # 挡住第二次释出，硬留一个 released 反而会误伤新株。
        cell.plant_state["released"] = 1

    done: dict[str, Any] = {}
    max_cells = max(1, int(release.max_cells))
    deposit_targets = ring_cells(state, x, y, radius=1)[:max_cells]
    # 每个通道的**真实作用格**：释出反应只画这些格。按半径补画会变成
    # 「动画比结算更大」，那是最容易骗过自己的假象。
    liquid_cells: list[tuple[int, int]] = []
    gas_cells: list[tuple[int, int]] = []
    push_cells: list[tuple[int, int]] = []
    ignite_cells: list[tuple[int, int]] = []
    integrity_cells: list[tuple[int, int]] = []
    electric_cells: list[tuple[int, int]] = []

    # 3) 液体（必须早于点火：先倒油，火才有燃料）
    if release.liquid:
        landed = _deposit_material(state, deposit_targets, release.liquid,
                                   release.amount, sink=liquid_cells)
        if landed:
            done["liquid"] = (release.liquid, landed)
    # 4) 搬气（压差囊：只搬走本格已有的气，不凭空造）
    if release.push_gas:
        moved = _push_gas(state, x, y, release.push_gas, sink=push_cells)
        if moved:
            done["push_gas"] = moved
    # 5) 气体
    if release.gas:
        landed = _deposit_material(state, deposit_targets, release.gas,
                                   release.amount, sink=gas_cells)
        if landed:
            done["gas"] = (release.gas, landed)
    # 6) 点火：只认真有燃料的格，最多 3 格，蔓延交给火焰规则。
    if release.ignite:
        lit = 0
        for nx, ny in ring_cells(state, x, y, radius=1):
            if lit >= int(release.ignite):
                break
            if state._ignite_cell(nx, ny, strength=2):
                lit += 1
                ignite_cells.append((nx, ny))
        if lit:
            done["ignite"] = lit
    # 7) 放电：本格 + 真实导通的四邻，≤3 格 / 1 回合，源名不进玩家电系预算。
    if release.electric:
        cells = [(x, y)]
        for dx, dy in _NEIGHBORS4:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < state.width and 0 <= ny < state.height):
                continue
            if state._conductive_cell(state.cell(nx, ny)):
                cells.append((nx, ny))
        cells = cells[: max(1, int(release.electric))]
        cells.sort(key=lambda pos: (pos != (x, y), pos[1], pos[0]))
        # source 不能带冒号：电场记账键按 ':' 分段解析，`plant:key` 会被当成
        # 四段而整条作废（看起来放了电、实际零格结算）。用连字符保持可读。
        state._charge_electric_field(
            cells, source=f"plant-{definition.key}", origin=(x, y), duration=1,
        )
        electric_cells.extend(cells)
        done["electric"] = len(cells)
    # 8) 发声：T1 环境短声 / T2 一次性巨响；都不带 full_alert 与 freeze_near。
    if release.sound:
        state._sound_pulse(
            x, y, int(release.sound), category="environment",
            source=tr(str(definition.name)), announce=bool(release.sound >= 6),
            emitter=None if holder is state.player else holder,
        )
        done["sound"] = int(release.sound)
    # 9) 削耐久（必须在移除植株之后：否则会先判到那株植物的 owner 逻辑）
    if release.integrity:
        hit = _apply_integrity(state, ring_cells(state, x, y, radius=1),
                               release.integrity, sink=integrity_cells)
        if hit:
            done["integrity"] = hit
    # 10) 征兆（最后挂：踩踏者不会因为前面几步的位移而错过判定）
    if release.portent:
        if _grant_portent(state, holder, release.portent):
            done["portent"] = release.portent

    if done:
        # ---- 释出反应（§11 settled 层；2026-10-26 起默认不播）------------
        # 只登记真实发生的通道、真实作用的格；顺序固定，保证同一场景每次
        # 重放的字符层序一致。声音不在这里登记——_sound_pulse 已经走了声波
        # 环通道，再发一次事件就是同一件事画两遍。
        #
        # 用户实测后下线：踩破/拔除那一下的字符动画观感差，而「放了什么、
        # 放了多少」播报文字已经说清。开关见 ``PLANT_REACTION_ANIMATIONS``。
        if plant_reaction_animations_enabled():
            for channel, cells in (
                ("liquid", liquid_cells),
                ("push_gas", push_cells),
                ("gas", gas_cells),
                ("ignite", ignite_cells),
                ("electric", electric_cells),
                ("integrity", integrity_cells),
            ):
                if channel in done and cells:
                    _emit_release_visual(state, definition, x, y, channel, cells)
            if "portent" in done and holder is not None:
                # 被缚的是人不是地形：画在触发者身上，才读得出「谁被缠住了」。
                _emit_release_visual(
                    state, definition, x, y, "portent",
                    [(holder.x, holder.y)],
                )
        done["detail"] = release_detail(done)
        if announce:
            state.messages.append(
                tr("{name}被破坏：{detail}。", name=tr(definition.name), detail=done["detail"]))
    return done


# 通道 -> (visual_key, tier)。tier 取配方自身的量级档，别在这里另立一套。
_RELEASE_VISUALS: dict[str, tuple[str, int]] = {
    "liquid": ("plant.release.liquid", 1),
    "push_gas": ("plant.release.push", 1),
    "gas": ("plant.release.gas", 1),
    "ignite": ("plant.release.fire", 2),
    "electric": ("plant.release.electric", 2),
    "integrity": ("plant.release.integrity", 1),
    "portent": ("plant.release.snare", 1),
}


def _emit_release_visual(state: Any, definition: Any, x: int, y: int,
                         channel: str, cells: list[tuple[int, int]]) -> None:
    """登记一次释出反应。只入旁路队列，不推进回合、不消耗 RNG、不改世界。"""
    visual_key, tier = _RELEASE_VISUALS[channel]
    from .visual_events import emit_visual
    emit_visual(
        state,
        # kind 就用配方名：否则「通道叫 ignite、配方叫 fire」，排查时要在两张
        # 表之间来回翻译，且日志里看不出该播哪一段。
        kind=visual_key,
        # impact 而非 release：释出就是那一下命中，配方层按 impact 门槛可见。
        outcome="impact",
        source=(x, y),
        targets=tuple(cells),
        affected_cells=tuple(cells),
        visual_key=visual_key,
        tier=tier,
        facts=(
            ("cells", len(cells)),
            ("plant", str(getattr(definition, "key", ""))),
            ("plant_code", int(getattr(definition, "code", 0) or 0)),
        ),
        layer_key="plant.release",
    )


def release_message(name: str, done: dict) -> str:
    """完整的释出播报（"X 被破坏：……。"）。"""
    return tr("{name}被破坏：{detail}。", name=tr(name), detail=release_detail(done))


def release_detail(done: dict) -> str:
    parts: list[str] = []
    if "liquid" in done:
        kind, amount = done["liquid"]
        parts.append(tr("{kind} {amount} 单位", kind=tr(kind), amount=amount))
    if "gas" in done:
        kind, amount = done["gas"]
        parts.append(tr("{kind} {amount} 单位", kind=tr(kind), amount=amount))
    if "push_gas" in done:
        parts.append(tr("推出 {amount} 单位气体", amount=done["push_gas"]))
    if "ignite" in done:
        parts.append(tr("点燃 {n} 处", n=done["ignite"]))
    if "electric" in done:
        parts.append(tr("放电 {n} 格", n=done["electric"]))
    if "sound" in done:
        parts.append(tr("发出 {n} 格声响", n=done["sound"]))
    if "integrity" in done:
        parts.append(tr("刮损 {n} 处地形", n=done["integrity"]))
    if "portent" in done:
        parts.append(tr("缠住触发者"))
    # 分隔符随语言走：英文播报里不能残留中文顿号。
    return ("，" if get_language() == "zh" else ", ").join(parts)


# ---- 常驻周期效果 ----------------------------------------------------------
def _absorb_once(state: Any, cell: Any, kind: str, *, gas: bool) -> bool:
    """从一格吸走 1 单位指定材料；成功返回 True。"""
    if gas:
        if cell.gas_kind != kind or cell.gas <= 0:
            return False
        cell.gas = max(0, cell.gas - 1)
        if cell.gas == 0:
            cell.gas_kind = ""
    else:
        if cell.liquid_kind != kind or cell.liquid <= 0:
            return False
        cell.liquid = max(0, cell.liquid - 1)
        if cell.liquid == 0:
            cell.liquid_kind = ""
    state._material_index_ready = False
    return True


def _purify_once(state: Any, x: int, y: int) -> tuple[int, int] | None:
    """R1 内挑一名有可洗征兆的生物，把其中一项缩短 1 回合。

    返回真正被洗的那名生物所在格；没有可洗目标时返回 ``None``——调用方靠
    它区分「洗掉了」和「白跑一趟」，也靠它决定要不要画收束印记。
    """
    from ..materials.portents import portent_def
    candidates: list[Any] = [state.player]
    candidates.extend(e for e in state.enemies if e.integrity > 0)
    reachable = set(ring_cells(state, x, y, radius=1))
    best = None
    for holder in candidates:
        if (holder.x, holder.y) not in reachable:
            continue
        washable = [
            pid for pid, turns in holder.portents.items()
            if turns > 0 and portent_def(pid) is not None and portent_def(pid).washable
        ]
        if not washable:
            continue
        # 已连续等待最久者优先：剩余回合最多的那条最“陈旧”。
        pid = max(washable, key=lambda item: holder.portents.get(item, 0))
        if best is None or holder.portents.get(pid, 0) > best[1]:
            best = (holder, holder.portents.get(pid, 0), pid)
    if best is None:
        return None
    holder, _turns, pid = best
    holder.portents[pid] = int(holder.portents[pid]) - 1
    if holder.portents[pid] <= 0:
        holder.portents.pop(pid, None)
        holder.portent_attach.pop(pid, None)
        holder.portent_debt.pop(pid, None)
    if holder is state.player:
        state.messages.append(tr("贤者之苔吸走了「{name}」的一小段。", name=tr(portent_def(pid).name)))
    return (int(holder.x), int(holder.y))


def _emit_periodic_visual(state: Any, definition: Any, kind: str,
                          cells: list[tuple[int, int]]) -> None:
    """登记一次常驻效果的真实作用（§11「每次实际吸收只对被扣单位的格」）。

    只发真实发生的那一格：预算耗尽、目标为空、被墙挡住时根本不调用。
    这也是「停回合观察十秒，材料量与预算不变」能成立的前提——事件只在
    真实回合推进时产生，装饰层不会自己多吸一次。
    """
    if not cells:
        return
    from .visual_events import emit_visual
    emit_visual(
        state,
        kind=kind,
        outcome="impact",
        source=cells[0],
        targets=tuple(cells),
        affected_cells=tuple(cells),
        visual_key=kind,
        tier=0,
        facts=(
            ("plant", str(getattr(definition, "key", ""))),
            ("plant_code", int(getattr(definition, "code", 0) or 0)),
        ),
        layer_key="plant.periodic",
    )


#: 踩踏/拔除时的字符动画已按用户实测下线（2026-10-26）：观感差，而且只是把
#: 「放了什么、放了多少」在格子上再演一遍——那件事播报文字与格子详情已经说清。
#: **保留开关而不是删干净**：配方与登记代码都还在，这一处置 True 即整批恢复；
#: 机制、结算、预算、播报文字与存档完全不受影响。
PLANT_REACTION_ANIMATIONS = False


def plant_reaction_animations_enabled() -> bool:
    """踩踏/拔除现在到底播不播字符动画（生产默认关；测试可临时打开）。"""
    return bool(PLANT_REACTION_ANIMATIONS)


def tick_periodic_plants(state: Any, amount: int) -> None:
    """按真实世界回合推进常驻植物的吸收／搬气／净化。

    只扫**角色身边**的植株（本格与 R1）：这些效果的作用半径本来就只有一格，
    离得远的株没有观察者也没有受害者，全图扫描只是白花时间。多个角色共享
    同一格时只结算一次（源株自己的预算）。
    """
    if amount <= 0:
        return
    actors = [state.player]
    actors.extend(e for e in state.enemies if e.integrity > 0)
    seen: dict[tuple[int, int], int] = {}
    for actor in actors:
        for pos in ring_cells(state, actor.x, actor.y, radius=1):
            seen.setdefault(pos, 0)
    rounds = min(int(amount), 30)
    for (x, y) in sorted(seen, key=lambda pos: (pos[1], pos[0])):
        cell = state.cell(x, y)
        code = cell.plant
        if not code:
            continue
        definition = plant_def_for(code)
        if not definition.has_periodic:
            continue
        budget_key = plant_budget_key(code)
        state_of_cell = cell.plant_state
        if not isinstance(state_of_cell, dict):
            state_of_cell = {}
            cell.plant_state = state_of_cell
        remaining = state_of_cell.get(budget_key)
        total = max(definition.absorb_gas_budget, definition.absorb_liquid_budget,
                    definition.push_gas_budget, definition.purify_budget)
        if remaining is None:
            remaining = total
        remaining = int(remaining)
        # 同一株在同一回合里连吸 3 单位也只该看见一次收束：按「格」去重，
        # 不按「单位」发。否则每单位一条事件会在同一格叠三层同样的字。
        absorb_cells: list[tuple[int, int]] = []
        flow_pairs: list[tuple[tuple[int, int], tuple[int, int]]] = []
        purify_cells: list[tuple[int, int]] = []
        for _ in range(rounds):
            if remaining <= 0:
                break
            acted = False
            if definition.absorb_gas_budget:
                for kind in definition.absorb_gas:
                    for nx, ny in ((x, y), *[(x + dx, y + dy) for dx, dy in _NEIGHBORS4]):
                        if not (0 <= nx < state.width and 0 <= ny < state.height):
                            continue
                        if _absorb_once(state, state.cell(nx, ny), kind, gas=True):
                            if (nx, ny) not in absorb_cells:
                                absorb_cells.append((nx, ny))
                            acted = True
                            break
                    if acted:
                        break
            if not acted and definition.absorb_liquid_budget:
                for kind in definition.absorb_liquid:
                    for nx, ny in ((x, y), *[(x + dx, y + dy) for dx, dy in _NEIGHBORS4]):
                        if not (0 <= nx < state.width and 0 <= ny < state.height):
                            continue
                        target = state.cell(nx, ny)
                        from .tamper_protection import liquid_reason
                        if target.liquid_kind and liquid_reason(target.liquid_kind):
                            continue
                        if _absorb_once(state, target, kind, gas=False):
                            if (nx, ny) not in absorb_cells:
                                absorb_cells.append((nx, ny))
                            acted = True
                            break
                    if acted:
                        break
            if not acted and definition.push_gas_budget:
                targets: list[tuple[int, int]] = []
                moved = _push_gas(state, x, y, 1, sink=targets)
                if moved and targets and ((x, y), targets[0]) not in flow_pairs:
                    # 流线只标真实源与真实目标；被墙挡住的这一次什么都不画。
                    flow_pairs.append(((x, y), targets[0]))
                acted = bool(moved)
            if not acted and definition.purify_budget:
                washed = _purify_once(state, x, y)
                if washed is not None and washed not in purify_cells:
                    purify_cells.append(washed)
                acted = washed is not None
            if not acted:
                break  # 没有可作用的目标：这一轮不扣预算
            remaining -= 1
        # 先落预算再登记：事件必须描述**已经结算完**的这一次，读者拿到的
        # 剩余量不能比事件里那一格还新。
        state_of_cell[budget_key] = max(0, remaining)
        state_of_cell["spent"] = total - max(0, remaining)
        if absorb_cells:
            _emit_periodic_visual(state, definition, "plant.absorb", absorb_cells)
        for source_cell, target_cell in flow_pairs:
            _emit_periodic_visual(
                state, definition, "plant.flow", [source_cell, target_cell])
        if purify_cells:
            _emit_periodic_visual(state, definition, "plant.purify", purify_cells)
