"""格子详情（docs §16）的逐对象数据口径：这一格有什么、允许看到什么、每项读数的来源。

这里只收集与判定，不排版——排版仍在 :meth:`ui.panels` 的 ``_cd_text``。
独立成模块的理由与 §19 的字段登记表相同：同一格的对象清单、每个对象的权限
边界、完整度上限的可信来源必须只有一份口径，格子详情、分层观察与测试都从
这里取；不能各自靠「这一格可见」这一个总开关再猜一遍。
"""

from __future__ import annotations

import math
from typing import Any

from ..data.anomalies import ANOMALY_DEFINITIONS
from ..i18n import tr
from ..materials import PORTENT_DEFINITIONS, SURFACE_KINDS, TABLE_KINDS

# 独立运行计时（§16.4）：各自列剩余回合，不合并成一个笼统「异常」。
# 驻足不在这里——它是征兆（materials/portents.py），走 portent_notes。
CONTROL_TIMERS = (
    ("frozen_turns", "冻结"),
    ("slow_turns", "迟缓"),
    ("blind_turns", "视野受限"),
)

# 未经普通观察时，一只生物凭什么被列出（§16.6 的对象级权限）。
# 这些是**中文键**：由显示点（panels._cd_creature_rows）经 tr() 取词，英文词条
# 登记在 i18n_ui_en。整句（拾取条件、用法）带插值，只能在这里即时取词。
SENSE_SIGHT = "视野"
SENSE_CORE = "核心执念恒显"
SENSE_REVEAL = "灵视揭示"
SENSE_ECHO = "残影直觉"
SENSE_SELF = "自身"
SENSE_SOURCES = (SENSE_SIGHT, SENSE_CORE, SENSE_REVEAL, SENSE_ECHO, SENSE_SELF)

# 完整度上限的可信来源（§16.4）：这条来源写在面板上，玩家才判断得了这个上限
# 能不能信。同为中文键，由显示点经 tr() 取词。
SOURCE_INSTANCE = "实例记录"
SOURCE_SPAWN = "出生值"
SOURCE_SEEN = "本层已见"
SOURCE_ESTIMATE = "内容表推算"
SOURCE_UNBASED = "无内容表依据"
INTEGRITY_SOURCES = (
    SOURCE_INSTANCE, SOURCE_SPAWN, SOURCE_SEEN, SOURCE_ESTIMATE, SOURCE_UNBASED,
)

# 承载位置（§16.5 的「位置」字段）。
SURFACE_TABLE = "台面"
SURFACE_GROUND = "地面"


def in_bounds(state: Any, x: int, y: int) -> bool:
    return 0 <= x < state.width and 0 <= y < state.height


def environment_authorized(state: Any, x: int, y: int) -> bool:
    """本格**实时环境**（液、气、植物、火焰、掉落物、事件）是否可见。

    ``GameState.is_visible`` 把「感觉到某个恒显生物」也算成整格可见，那是渲染
    需要的兼容行为；详情面板不能跟着把整格摊开（§16.6「恒显对象不带出隐藏
    掉落」），所以这里只认普通观察（视线/照彻/发光地衣）与已显影记忆。
    """
    if not in_bounds(state, x, y):
        return False
    return state.live_sight(x, y) or (x, y) in state.developed_for_depth()


def creatures_at(state: Any, x: int, y: int) -> list[Any]:
    """本格全部存活实体：玩家与所有生物分别列出。

    与 ``state.entity_at`` 的关键差别是**不提前结束**——旧详情走 ``entity_at``，
    玩家同格时只回「你自己」，把同格其他实例整个遮掉（§16.2）。顺序稳定：
    玩家在前，其余按 ``state.enemies`` 的登记顺序（同名实例靠序号区分，
    不合并成一条）。
    """
    found = []
    if (state.player.x, state.player.y) == (x, y) and state.player.integrity > 0:
        found.append(state.player)
    found.extend(
        enemy for enemy in state.enemies
        if enemy.integrity > 0 and (int(enemy.x), int(enemy.y)) == (x, y)
    )
    return found


def sensed_creatures(state: Any, x: int, y: int) -> list[tuple[Any, str]]:
    """视野外仅凭「存在性感知」授权的生物，连同授权来源。

    前三条与 :meth:`SightMixin.perceived_creatures` / 观测详情同源；「残影直觉」
    是地图渲染早已公开的侦查（core/map_scene.py 的 sensed 集合），这里只是把
    同一份边界带到详情，不额外给出完整度之类未经观察的读数。
    """
    found: list[tuple[Any, str]] = []
    seen_ids = set()
    for enemy in state.perceived_creatures(x, y):
        definition = ANOMALY_DEFINITIONS.get(getattr(enemy, "catalog_id", ""), {})
        core = definition.get("anomaly_kind") == "核心执念"
        found.append((enemy, SENSE_CORE if core else SENSE_REVEAL))
        seen_ids.add(id(enemy))
    if state.insight_active("残影直觉"):
        radius = state.effective_sight_radius()
        for enemy in state.enemies:
            if enemy.integrity <= 0 or id(enemy) in seen_ids:
                continue
            if (int(enemy.x), int(enemy.y)) != (x, y):
                continue
            if enemy.trait not in ("phantom", "disguise"):
                continue
            if max(abs(enemy.x - state.player.x), abs(enemy.y - state.player.y)) <= radius:
                found.append((enemy, SENSE_ECHO))
    return found


def authorized_creatures(state: Any, x: int, y: int) -> list[dict[str, Any]]:
    """本格**允许列出**的生物清单，一条一个实例。

    普通观察之下=全部；视野外=只列出被感知到的那几只。``observed`` 表示这只
    生物的完整度/征兆/技能是否经过观测（残影直觉只到「知道是谁」为止）。
    """
    if environment_authorized(state, x, y):
        entries = []
        for entity in creatures_at(state, x, y):
            if entity is state.player:
                entries.append({"entity": entity, "sense": SENSE_SELF, "observed": True})
            else:
                entries.append({"entity": entity, "sense": SENSE_SIGHT, "observed": True})
        return entries
    return [
        {"entity": entity, "sense": sense, "observed": sense != SENSE_ECHO}
        for entity, sense in sensed_creatures(state, x, y)
    ]


def display_identity(state: Any, entity: Any) -> tuple[str, bool]:
    """显示名与「是否仍是表面身份」：伪装沿用地图那一份口径，不泄露真名。"""
    from ..core.map_scene import actor_display

    name, _icon = actor_display(state, entity)
    return str(name), str(name) != str(entity.label)


def integrity_bounds(state: Any, entity: Any) -> dict[str, Any]:
    """完整度与其**有来源**的上限；推算不出来的明说，不拿内容表基础值冒充。

    实例上限有三种可信度（§16.4）：

    1. 生成时记下的（``active_skill_state['max_integrity']``：终层统计、医院、
       图书馆那条路径）——直接可信；
    2. 与内容表推算值恰好相等（开局原样出生，没被缩放也没被衍生覆盖）——可信；
    3. 其余都不可信：深层缩放、开局强度倍率、分裂残影/医院膜等的 integrity
       覆盖都会让「内容表基础值」不等于这一只的真实上限，只能标注成推算或
       已见最高，由调用方打上问号。
    """
    current = int(entity.integrity)
    recorded = 0
    state_map = getattr(entity, "active_skill_state", None) or {}
    try:
        recorded = int(state_map.get("max_integrity") or 0)
    except (TypeError, ValueError):
        recorded = 0
    if recorded:
        return {"current": current, "max": max(recorded, current),
                "source": SOURCE_INSTANCE, "confirmed": recorded >= current}
    definition = ANOMALY_DEFINITIONS.get(getattr(entity, "catalog_id", ""), {})
    base = int(definition.get("integrity", 0) or 0)
    if base <= 0:
        return {"current": current, "max": current,
                "source": SOURCE_UNBASED, "confirmed": False}
    expected = max(1, round(base * float(state._enemy_integrity_mult())))
    if current == expected:
        return {"current": current, "max": current,
                "source": SOURCE_SPAWN, "confirmed": True}
    if current > expected:
        return {"current": current, "max": current,
                "source": SOURCE_SEEN, "confirmed": False}
    return {"current": current, "max": expected,
            "source": SOURCE_ESTIMATE, "confirmed": False}


def control_timers(entity: Any) -> list[tuple[str, int]]:
    """冻结/迟缓/失明的独立剩余回合（向上取整：还在生效就至少还剩 1 回合）。"""
    timers = []
    for attribute, name in CONTROL_TIMERS:
        value = float(getattr(entity, attribute, 0.0) or 0.0)
        if value > 0:
            timers.append((name, int(math.ceil(value))))
    return timers


def portent_notes(state: Any, entity: Any) -> list[dict[str, Any]]:
    """征兆逐条：统一机制名称 + 性质 + 层数 + 剩余回合 + 材料附着。

    层/回合各自为 0 就不写（与玩家征兆栏同一口径，见 PortentsMixin
    ``active_portents`` 的「先层后回合」）；附着是「还粘着材料的续期账」，
    单独写出，避免玩家以为剩余回合凭空变长。
    """
    notes: list[dict[str, Any]] = []
    for portent_id in entity.portents:
        definition = PORTENT_DEFINITIONS.get(portent_id)
        if definition is None:
            continue
        stacks = entity.portent_stacks.get(portent_id, definition.stacks)
        notes.append({
            "id": portent_id,
            "name": definition.name,
            "kind": definition.kind,
            "effect": definition.effect,
            "remaining": int(state.portent_remaining(entity, portent_id)),
            "stacks": int(stacks or 0),
            "attach": int(entity.portent_attach.get(portent_id, 0) or 0),
        })
    notes.sort(key=lambda note: note["name"])
    return notes


def is_tabletop(state: Any, x: int, y: int) -> bool:
    """本格算不算「台面」承载（§16.3 的台面层）。

    2026-10-22：判据从 `TABLE_KINDS` 换成 `SURFACE_KINDS`——白瓷工作台与
    胡桃木书架是可步行的家具，但它们**搁得住东西、伸得出手**，玩家看到的
    行为跟台子完全一样；不换的话，「从台面取下」这条提示对它们永远不出现。
    """
    return state.cell(x, y).wall_kind in SURFACE_KINDS


def surface_kind(state: Any, x: int, y: int) -> str:
    """本格是台面还是地面（§16.5 的「位置」字段）。

    第十四节的通用支撑关系还没落地，所以这里只认台种登记（木桌子/石台/
    陷阱石台/机关石台）；那些格子上的显化物按 G 是「从台面取下」，与脚下
    地面拾取是两条路径。
    """
    return SURFACE_TABLE if is_tabletop(state, x, y) else SURFACE_GROUND


def item_entries(state: Any, x: int, y: int) -> list[dict[str, Any]]:
    """本格全部显化物，逐件一条（含当前不能直接取得的原因）。

    ``collect_items`` 的语义是「从上往下依次放入、装不下的留在原地」，所以
    这里列全部、不截断，也不把「拿不动」写成「不存在」（§16.5）。
    """
    surface = surface_kind(state, x, y)
    table = surface == SURFACE_TABLE
    player = state.player
    on_cell = (int(player.x), int(player.y)) == (x, y)
    near = max(abs(player.x - x), abs(player.y - y)) <= 1
    used = int(state.inventory_used)
    capacity = int(state.inventory_capacity)
    # 承载面归属（2026-10-22）：有主的台面把「归谁、取一件付什么」直接写在
    # 每一件物品下面——方案 §P1 要求「所有权与领取费用可见」，藏在动作失败
    # 提示里不算可见。
    from ..core.surface_terms import terms_note

    surface_note = terms_note(state.cell(x, y).wall_kind) if table else ""
    entries: list[dict[str, Any]] = []
    for entry in state.pickup_candidates(x, y):
        item = entry.item
        blockers: list[str] = []
        if table:
            if not near:
                blockers.append(tr("走到台面旁边后从台面取下（G）"))
        elif not on_cell:
            blockers.append(tr("走进这一格后拾取（G）"))
        if used >= capacity:
            blockers.append(tr(
                "行囊已满（{used}/{capacity}），装不下的会留在原地。",
                used=used, capacity=capacity))
        entries.append({
            "entry": entry,
            "item": item,
            "surface": surface,
            "surface_note": surface_note,
            "blockers": blockers,
            "usable_now": not blockers,
        })
    return entries


def usage_hint(state: Any, item: Any) -> str:
    """入袋之后怎么用（§16.5「已知使用方式」）：只按行囊里的真实键位说。"""
    if state._placeable_slot(item):
        return tr("入袋后可整理联想盘（U）· D 放下 · Q 投掷")
    if getattr(item, "slot", ""):
        return tr("入袋后可携带/卸下（U）· D 放下 · Q 投掷")
    return tr("入袋后可使用（U）· D 放下 · Q 投掷")


def construct_hint(item: Any) -> str:
    """构件类配方提示：这件东西跟哪套打法配起来才成立（方案 P3 尾巴）。

    单列一个函数而不是塞进 ``usage_hint``：用法讲**按键**，配合讲**战术**，
    两句话分两行，玩家扫一眼就能分开。
    """
    from ..data.construct_pairs import pair_hint

    return pair_hint(getattr(item, "definition_id", ""))
