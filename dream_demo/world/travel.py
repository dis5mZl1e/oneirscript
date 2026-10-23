"""跨层行程（重构方案 §6.3）：换层时的轻量迁移与合法投影。

三条硬边界：

* 未加载楼层不跑任何模拟——行程只在**成功的换层事件**上推进一格，
  纯读档、开菜单、远层重建都不推进（§6.3「后台不会悄悄杀掉委托人」）；
* 一次换层最多推进一位满足条件的重要角色，由 :func:`on_descend` 保证；
* 同一 ``actor_uid`` 全局只有一位（§12.2）：投影（到站角色在目标层落成
  实体）与旧层残留清理都在层物化路径上由 :func:`reconcile_layer` 原子完成，
  快照里留下的旧影会在下次还原时对账删除，不会出现「两层各有一份」。

行程数据全部住在 :class:`~dream_demo.world.ledger.ActorRecord` 预留的字段里
（``itinerary``／``next_stop``／``travel_stage``），随世界记录一起持久化——
本模块不持有任何状态，只读账本、改账本字段。层键沿用 ``GameState.layer_key()``
的主梦口径（纯数字串）；梦中梦层（``R…``）没有主梦行程，对账直接跳过。

V1 名册只有引路人（§6.3 的示例角色）；后续任务链（「下一站等你」）落地时
再按定义表的 ``important`` 标记扩册。
"""
from __future__ import annotations

import random
import zlib
from typing import Any

from ..i18n import tr

#: V1 行程名册（§6.3「每个重要角色记录行程」的首版实施范围）。
TRAVEL_ROSTER: frozenset[str] = frozenset({"npc.guide"})
#: 停靠层深度边界：1 层以下没有行程意义，28+ 是收尾层（epilogue）。
TRAVEL_MIN_DEPTH = 1
TRAVEL_MAX_DEPTH = 27
#: ``travel_stage`` 取值：启程后「在途」，走完行程表「已到达」。
STAGE_MOVING = "在途"
STAGE_ARRIVED = "已到达"


def _npc_label(npc_kind: str) -> str:
    from ..data.npcs import NPC_DEFINITIONS
    definition = NPC_DEFINITIONS.get(npc_kind) or {}
    return definition.get("name") or npc_kind


def _home_depth(record: Any) -> int | None:
    """主梦层的层键是纯数字串；梦中梦/异常键没有深度轴，返回 None。"""
    key = record.home_layer_key
    return int(key) if key.isdigit() else None


def plan_itinerary(record: Any, *, seed: int) -> bool:
    """给还没有行程的名册角色定 1–2 个停靠层（§6.3「生成期应提前选择」）。

    随机流用「局种子 + actor_uid 校验和」——同一位角色在同一局里重复规划
    会得到同一份行程；行程随世界记录持久化，远层重建/读档都不会重抽。
    返回是否真的规划了行程（名册外/已有行程/无合法停靠层都是 False）。
    """
    if record.itinerary or record.npc_kind not in TRAVEL_ROSTER:
        return False
    home = _home_depth(record)
    if home is None:
        return False
    rng = random.Random(seed * 7919 + zlib.crc32(record.actor_uid.encode("utf-8")))
    direction = 1 if rng.random() < 0.5 else -1
    stops: list[str] = []
    cursor = home
    for _ in range(2):
        nxt = cursor + direction * rng.randint(1, 2)
        if not TRAVEL_MIN_DEPTH <= nxt <= TRAVEL_MAX_DEPTH or nxt == home:
            break
        stops.append(str(nxt))
        cursor = nxt
    if not stops:
        return False
    record.itinerary = tuple(stops)
    record.next_stop = stops[0]
    record.travel_stage = STAGE_MOVING
    return True


def _has_active_task(ledger: Any, actor_uid: str) -> bool:
    """这位是不是某一单「进行中」委托的委托人。

    委托人先别跑路（§6.3「任务交付由本人、具名代收点或派系服务台承担」——
    代收点还没有，V1 先让活委托的委托人留在原地），交付完毕再继续行程。
    """
    return any(task.giver_uid == actor_uid and task.status == "进行中"
               for task in ledger.tasks.values())


def on_descend(state: Any, *, from_depth: int) -> None:
    """成功下潜一层的收尾钩子：推进至多一位在途角色（§6.3）。

    只推进、不投影——投影统一发生在层物化路径的 :func:`reconcile_layer`，
    这样「推进进刚进入的这一层」的角色会在随后的物化里直接现身。
    若动身的角色先前就在玩家刚离开的那一层，顺手给一句去向消息：
    玩家亲眼看着他走，比事后对着空摊位犯疑好（§6.3「有消息/路标可查」）。
    """
    ledger = state.world_ledger
    from_key = str(from_depth)
    for record in sorted(ledger.actors.values(), key=lambda r: r.actor_uid):
        if record.npc_kind not in TRAVEL_ROSTER or not record.alive:
            continue
        if not record.itinerary:
            if not plan_itinerary(record, seed=state.seed):
                continue
        if not record.next_stop or record.travel_stage == STAGE_ARRIVED:
            continue
        if _has_active_task(ledger, record.actor_uid):
            continue
        was_nearby = record.layer_key == from_key
        record.layer_key = record.next_stop
        index = record.itinerary.index(record.next_stop)
        following = record.itinerary[index + 1] if index + 1 < len(record.itinerary) else ""
        record.next_stop = following
        record.travel_stage = STAGE_MOVING if following else STAGE_ARRIVED
        if was_nearby:
            state.messages.append(tr(
                "「{name}」动身去了别处——你说不准会在哪层再碰上。",
                name=_npc_label(record.npc_kind)))
        return  # §6.3：一次换层最多迁移一位已满足条件的重要角色。


def suppress_random_spawn(state: Any, npc_kind: str) -> bool:
    """本层还该不该从投放表生成这个职业？只看一种情况：外来户在场。

    别层来的同职业正在这层作客时，随机池再抽一位就是双胞胎——抑制。
    至于「本地户走了」的情形**不**在这里拦：重建会照常铸出同 uid 的
    实体并合并回旅人的既有档案，而 ``reconcile_layer`` 会在物化收尾把
    「账上已走」的这份僵尸清掉——净效果就是空位，且全程确定性成立。
    场景绑定的具名 NPC 同样吃这条（旅人占位期间不给具名位翻版）。
    """
    here = state.layer_key()
    return any(record.alive and record.npc_kind == npc_kind
               and record.home_layer_key != here and record.layer_key == here
               for record in state.world_ledger.actors.values())


def _legal_arrival(state: Any, x: int, y: int) -> bool:
    if not (0 <= x < state.width and 0 <= y < state.height):
        return False
    cell = state.cell(x, y)
    if cell.solid:
        return False
    return state.entity_at(x, y) is None


def _nearest_legal(state: Any, x: int, y: int) -> tuple[int, int] | None:
    """从目标格向外一圈圈找最近合法落点（螺旋序，别把结构撞开——旅人不施工）。"""
    if _legal_arrival(state, x, y):
        return x, y
    for radius in range(1, 13):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue  # 只扫当前圈边，不重扫内部。
                if _legal_arrival(state, x + dx, y + dy):
                    return x + dx, y + dy
    return None


def _project(state: Any, record: Any) -> bool:
    """把到站角色投影成本层实体：沿用登记路径的站位清理（脚下不留流体）。"""
    spot = _nearest_legal(state, record.x, record.y)
    if spot is None:
        return False
    x, y = spot
    cell = state.cell(x, y)
    cell.liquid = 0
    cell.liquid_kind = ""
    cell.gas = 0
    cell.gas_kind = ""
    if cell.plant:
        state.set_plant(x, y, 0)
    state._add_npc(record.npc_kind, x, y, actor_uid=record.actor_uid)
    record.x, record.y = x, y
    return True


def reconcile_layer(state: Any) -> None:
    """层物化（生成或快照还原）之后的行程对账——§12.2「原子执行」的落点。

    ① 旧影清除：账上已经去了别层、层上还站着的（快照里留下的）实体删掉；
       用**重建列表**而不是原地增删——快照里的列表和本层共享同一对象，
       原地改动会把快照本身改坏。
    ② 到站投影：账上在本层、家里不在本层、层上还没有实体的角色落成实体。
       落点先记账坐标，不合法就就近找合法格；实在落不下就保持未现形，
       下次物化再对账（不硬塞、不砸墙）。

    纯对账：不推进行程、不产事实、不改立场。梦中梦层直接跳过。
    """
    ledger = state.world_ledger
    here = state.layer_key()
    if not here.isdigit():
        return
    kept: list[Any] = []
    for enemy in state.enemies:
        uid = getattr(enemy, "actor_uid", "")
        record = ledger.actor(uid) if uid else None
        if record is not None and record.layer_key != here:
            continue  # ① 账上已走：本层的这一位是旧影。
        kept.append(enemy)
    if len(kept) != len(state.enemies):
        state.enemies = kept
    present = {getattr(enemy, "actor_uid", "") for enemy in kept}
    for uid in sorted(ledger.actors):
        record = ledger.actors[uid]
        if (record.alive and record.layer_key == here
                and record.home_layer_key != here and uid not in present):
            if _project(state, record):
                present.add(uid)
