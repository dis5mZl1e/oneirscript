"""事件执行器：根事件、因果预算、共享冷却与插片反馈（§5.5、§5.6）。

新增反馈一律标记为派生：不吃深度倍率、不乘共鸣，不触发吸血、击杀回流、
折射印记、挂钩、装备命中链等再次奖励。反馈先验证条件、目标和预计实际
变化，成功才扣费并写冷却。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .board import PIECE_SPECS, PRIORITY_VECTORS, ROOT_ENDPOINTS
from .grammar import board_signature, compile_board, semantics_of_placement
from .links import MAX_PENDING, ReactPath, resume_paths

FEEDBACK_PER_ROUND = 1
FEEDBACK_PER_EVENT = 2
DEFAULT_COOLDOWN = 6
BUFFER_DURATION = 3
SURGE_AMOUNT = 5
EMBER_STRENGTH = 1
VOICE_RADIUS = 2
# 留白门：线路上没有任何留白装备时的系统阈值（§5.4 明确要求写死一个数）。
BLANK_GATE_DEFAULT = 10

# 与 materials_sim 的导电判定同一口径（不硬编码一种水）。
CONDUCTIVE_LIQUIDS = frozenset({"水", "导电液态记忆"})

ENDPOINT_IDS = tuple(endpoint[0] for endpoint in ROOT_ENDPOINTS)


@dataclass
class RootEvent:
    endpoint: str
    action_id: int = 0
    cell: tuple[int, int] | None = None
    previous_cell: tuple[int, int] | None = None
    target: Any = None
    material: str = ""
    damage_kind: str = ""
    derived: bool = False
    # 一次根事件的反馈名额（§5.5：最多 2 次，只用于跨回合延迟／分流）。
    # 「已访问节点」由线路自己带着（ReactPath.nodes，入档时写进待释放脉冲），
    # 这里不再复制一个没人读的同名字段。
    budget: int = FEEDBACK_PER_EVENT


@dataclass
class FeedbackResult:
    piece_id: str
    ok: bool
    reason: str = ""
    detail: dict = field(default_factory=dict)


def conductive_at(state, cell: tuple[int, int] | None) -> bool:
    """导电判定只许问材料层（§5.2：必须调用既有材料判定 API）。

    自己重写一份「液体≥8 且种类在表里」会漏掉金属聚合物——干地上的金属聚合物
    在电场里本来就是导体，副本判据会把已经导电的格子判成不导电。
    """
    if cell is None or not state.inside_board(*cell):
        return False
    return state._conductive_cell(state.cell(*cell))


def paths_for(state, endpoint: str) -> list[ReactPath]:
    compiled = state.equipment.compiled()
    return [p for p in compiled.react_paths if p.endpoint == endpoint]


def cooldown_ready(state, piece_id: str) -> bool:
    return state.time >= int(state.board_cooldowns.get(piece_id, 0))


def cooldown_remaining(state, piece_id: str) -> int:
    return max(0, int(state.board_cooldowns.get(piece_id, 0)) - state.time)


def _enemy_candidates(state, cell: tuple[int, int] | None, *, require_wet: bool) -> list:
    """稳定选择：最短合法距离、世界坐标、实例标识；必须当前可见、敌对、未隔实墙。

    「不读取未知位置，不隔实墙输出」（§5.5）不能只看 `is_visible` 的格子标记：
    视线走与异象感知同一个 Bresenham API，隔着一堵实墙的近处敌人不算合法落点。
    """
    if cell is None:
        return []
    candidates = []
    for enemy in state.enemies:
        if enemy.integrity <= 0 or enemy.relation != "失控意识":
            continue
        if not state.is_visible(enemy.x, enemy.y):
            continue
        distance = abs(enemy.x - cell[0]) + abs(enemy.y - cell[1])
        if distance > 2:
            continue
        if not state._has_line_of_sight(cell[0], cell[1], enemy.x, enemy.y):
            continue
        if require_wet and not (
            conductive_at(state, (enemy.x, enemy.y))
            or any(
                key in getattr(enemy, "portent_attach", {}) or {}
                for key in ("过电", "湿润")
            )
        ):
            continue
        key = getattr(enemy, "entity_id", None) or f"{enemy.label}@{enemy.x},{enemy.y}"
        candidates.append((distance, enemy.x, enemy.y, str(key), enemy))
    return sorted(candidates, key=lambda entry: entry[:4])


def _pick_wet_enemy(state, cell: tuple[int, int] | None):
    found = _enemy_candidates(state, cell, require_wet=True)
    return found[0][4] if found else None


def _destination_cell(state, path: ReactPath,
                      event: RootEvent) -> tuple[tuple[int, int] | None, str]:
    """落点解析（§5.5），返回 (格子, 失败原因)。

    默认档是原事件的目标格；受击链的「事件格」本来就是玩家脚下（见
    ``GameState._note_board_hurt``），所以不需要为它另开一条分支。
    「近处可见敌人」要线路上有「照」语义——缺语义时**拒发**而不是悄悄退回
    事件格，免得玩家以为打的是敌人、实际烧了别的位置。
    """
    piece = next(
        (p for p in state.board.pieces
         if p.piece_id == path.terminal_piece and (p.x, p.y) == path.terminal),
        None,
    )
    policy = piece.destination_policy if piece else "event_cell"
    if policy == "player_cell":
        return (state.player.x, state.player.y), ""
    if policy == "previous_cell":
        if not event.previous_cell:
            return None, "事件没有记录上一格"
        return event.previous_cell, ""
    if policy == "visible_enemy":
        if "照" not in path.semantics:
            return None, "落点设为近处可见敌人，但线路上没有「照」语义"
        found = _enemy_candidates(state, event.cell, require_wet=False)
        if not found:
            return None, "事件格附近 2 格内没有可见敌人"
        enemy = found[0][4]
        return (enemy.x, enemy.y), ""
    return event.cell, ("" if event.cell else "事件没有携带落点格")


def _try_spark(state, path: ReactPath, event: RootEvent) -> FeedbackResult:
    cell, reason = _destination_cell(state, path, event)
    if cell is None:
        return FeedbackResult("spark", False, reason)
    target = _pick_wet_enemy(state, cell)
    if target is None:
        return FeedbackResult("spark", False, "附近没有被液体浸湿的敌人。")
    if target.integrity <= 0:
        return FeedbackResult("spark", False, "目标已不存在")
    target.integrity -= 1
    return FeedbackResult("spark", True, detail={"target": target.label, "damage": 1})


def _drain_liquid(state, cell, kind: str, amount: int) -> int:
    """真实取走液体。`_add_liquid` 只加不减，扣减必须自己走同一套混合口径，
    否则「移涌」会把液体凭空复制一份（总量不守恒）。"""
    removed = min(amount, cell.liquid)
    if removed <= 0:
        return 0
    remaining = cell.liquid - removed
    cell.liquid_kind, cell.liquid = state._mix_liquids({kind: remaining})
    state._material_index_ready = False
    return removed


def _try_surge(state, path: ReactPath, event: RootEvent) -> FeedbackResult:
    """移涌：液体来源**始终**是事件格，编辑器只设目的格的优先方向（§5.5）。

    这里刻意不走 `_destination_cell`：把落点档位当成「抽哪一格」，玩家就能用
    一个玩家格落点把远处的水搬到自己脚下，等于凭空多出一条搬运链。
    """
    cell = event.cell
    if cell is None or not state.inside_board(*cell):
        return FeedbackResult("surge", False, "事件格不在场内")
    source = state.cell(*cell)
    if source.liquid <= 0 or source.liquid_kind not in CONDUCTIVE_LIQUIDS:
        return FeedbackResult("surge", False, "事件格没有可转移的导电液体")
    if getattr(source, "locked", False):
        return FeedbackResult("surge", False, "机关锁定的液体不可移动")
    order = sorted(PRIORITY_VECTORS, key=lambda d: (
        state.cell(cell[0] + d[0], cell[1] + d[1]).liquid
        if state.inside_board(cell[0] + d[0], cell[1] + d[1]) else float('inf'),
        cell[1] + d[1], cell[0] + d[0]))
    for dx, dy in order:
        target_cell = (cell[0] + dx, cell[1] + dy)
        if not state.inside_board(*target_cell):
            continue
        target = state.cell(*target_cell)
        if target.solid or getattr(target, "locked", False):
            continue
        if target.liquid_kind and target.liquid_kind != source.liquid_kind and target.liquid > 0:
            continue
        amount = min(SURGE_AMOUNT, source.liquid, max(0, 100 - target.liquid))
        if amount <= 0:
            continue
        kind = source.liquid_kind
        _drain_liquid(state, source, kind, amount)
        state._add_liquid(target, kind, amount)
        return FeedbackResult("surge", True, detail={"amount": amount, "kind": kind,
                                                     "to": target_cell})
    return FeedbackResult("surge", False, "相邻位置没有足够容量接收液体。")


def _try_buffer(state, path: ReactPath, event: RootEvent) -> FeedbackResult:
    current = state.board_buffer
    if current.get("points", 0) >= PIECE_SPECS["buffer"].capacity:
        return FeedbackResult("buffer", False, "缓冲已满")
    state.board_buffer = {
        "points": 1,
        "kind": event.damage_kind or "any",
        "until": state.time + BUFFER_DURATION,
    }
    return FeedbackResult("buffer", True, detail={"kind": event.damage_kind or "any"})


def _try_ember(state, path: ReactPath, event: RootEvent) -> FeedbackResult:
    """余温片：调用统一点燃入口，输入强度不超过 1，后续燃烧走原模拟。

    ``by_player`` 刻意传 False：这是联想的派生反馈，不是玩家亲手点火，
    因此不该顺手把「灰烬撤步」一类只认亲手那次的奖励也带出来（§5.5）。
    """
    cell, reason = _destination_cell(state, path, event)
    if cell is None:
        return FeedbackResult("ember", False, reason)
    if not state.inside_board(*cell):
        return FeedbackResult("ember", False, "落点不在场内")
    if not state._ignite_cell(cell[0], cell[1], EMBER_STRENGTH):
        return FeedbackResult("ember", False, "这个位置没有可点燃的材料。")
    return FeedbackResult("ember", True, detail={"cell": cell, "strength": EMBER_STRENGTH})


def _try_voice(state, path: ReactPath, event: RootEvent) -> FeedbackResult:
    """传声片：在事件格／上一位置发一次半径不超过 2 的声源，复用既有引诱规则。

    不硬控、不伤害，所以 ``freeze_near`` 恒为 0；半径直接传 2 而不过
    ``_sound_radius``——那是给「玩家自己发出的声响」做环境放大的，
    经它一遍就会超出方案规定的上限。
    """
    cell, reason = _destination_cell(state, path, event)
    if cell is None:
        return FeedbackResult("voice", False, reason)
    if not state.inside_board(*cell):
        return FeedbackResult("voice", False, "落点不在场内")
    heard = [
        enemy for enemy in state.enemies
        if enemy.integrity > 0 and enemy.trait not in ("staircase",)
        and abs(enemy.x - cell[0]) + abs(enemy.y - cell[1]) <= VOICE_RADIUS
    ]
    if not heard:
        return FeedbackResult("voice", False, "半径内没有听得见的失控意识")
    state._sound_pulse(cell[0], cell[1], VOICE_RADIUS)
    return FeedbackResult("voice", True, detail={"cell": cell, "reached": len(heard)})


EXECUTORS = {
    "spark": _try_spark,
    "surge": _try_surge,
    "buffer": _try_buffer,
    "ember": _try_ember,
    "voice": _try_voice,
}
def consume_buffer(state, kind: str) -> int:
    """缓冲只抵扣下一次创伤，不恢复已损失的心智／清醒，不叠成无限盾。"""
    data = state.board_buffer
    if not data.get("points"):
        return 0
    if int(data.get("until", 0)) < state.time:
        state.board_buffer = {}
        return 0
    if data.get("kind") not in ("any", kind):
        return 0
    state.board_buffer = {}
    return 1


def _blank_threshold(state, path: ReactPath) -> int:
    """留白门阈值：线路上留白装备的原阈值；一件都没有时取系统阈值 10。

    只认带阈值的留白件（blank_edge 的 power_secondary）；半页空稿那类
    「每层免一次成本」的留白件没有阈值，不参与，也不把门压到 0。
    """
    on_path = {node[1] for node in path.nodes if node[0] == "item"}
    from .senses import resolve
    meanings = [resolve(p.definition_id, p.sense_id) for p in state.board.placements
                if p.instance_id in on_path and p.sentence_written]
    thresholds = [
        int(meaning.power_secondary) for meaning in meanings
        if meaning.effect in ('blank_edge', 'blank_pass') and meaning.power_secondary
    ]
    return max(thresholds) if thresholds else BLANK_GATE_DEFAULT


def _path_blocked(state, path: ReactPath, event: RootEvent) -> str:
    """线路级门槛。空串表示放行，否则是不放行的原因（供预览与日志共用）。"""
    spec = PIECE_SPECS.get(path.terminal_piece or "")
    if spec is None or not (spec.feedback or spec.delay):
        return "终端不是反馈插片"
    if spec.requires and spec.requires not in path.semantics:
        return f"线路缺少「{spec.requires}」语义"
    from .grammar import output_allowed
    if path.deferred and not any(output_allowed(state.board, node, path.semantics) for node in path.continuation):
        return '这一分句没有能够成立的后续联想'
    if path.deferred:
        from .links import resume_paths
        branches = resume_paths(state.board, path, semantics_of_placement)
        if not any(not _path_blocked(state, branch, event) for branch in branches):
            return '这一分句的后续条件还没有满足'
    if path.gated and not conductive_at(state, event.cell):
        return "湿润门未通过：事件格没有有效导电液体"
    if path.blank_gated and state.imagination > _blank_threshold(state, path):
        return "留白门未通过：想象力高于阈值"
    return ""


def _run_feedback(state, path: ReactPath, event: RootEvent) -> FeedbackResult | None:
    """结算一条线路的终端反馈。先验证条件、目标和预计实际变化，成功才扣费写冷却。"""
    piece_id = path.terminal_piece or ""
    if _path_blocked(state, path, event):
        return None
    spec = PIECE_SPECS[piece_id]
    if not cooldown_ready(state, piece_id) or state.imagination < spec.cost:
        return None
    executor = EXECUTORS.get(piece_id)
    if executor is None:
        return None
    result = executor(state, path, event)
    if not result.ok:
        return result
    from ..core.settlement import REASON_STORY, settle_delta
    settle_delta(state, 'imagination', -spec.cost, reason=REASON_STORY,
                 source='事件选项代价')
    state.board_cooldowns[piece_id] = state.time + spec.cooldown
    state.board_feedback_round += 1
    state.messages.append(_feedback_message(state, piece_id, result))
    return result


def _pending_record(state, path: ReactPath, event: RootEvent) -> dict:
    """留声片存下的脉冲。全是可 JSON 序列化的原始值——待释放脉冲要入档。"""
    spec = PIECE_SPECS[path.terminal_piece or ""]
    node, arrival_cell, arrival_dir = path.deferred
    return {
        "piece": path.terminal_piece,
        "cell": list(path.terminal or ()),
        "endpoint": path.endpoint,
        "nodes": [list(item) for item in path.nodes],
        "semantics": sorted(path.semantics),
        "gated": bool(path.gated),
        "blank_gated": bool(path.blank_gated),
        "equipment_count": int(path.equipment_count),
        "deferred": [list(node), list(arrival_cell), arrival_dir],
        "continuation": [list(node) for node in path.continuation],
        'output_conditions': [[list(node), wet, low] for node, wet, low in path.output_conditions],
        "event": {
            "cell": list(event.cell) if event.cell else None,
            "previous_cell": list(event.previous_cell) if event.previous_cell else None,
            "material": event.material,
            "damage_kind": event.damage_kind,
            "action_id": int(event.action_id),
        },
        # 存脉冲自己就算一次反馈，留给下游的名额要先扣掉一格。
        "budget": max(0, int(event.budget) - 1),
        "due": state.time + spec.delay,
        "expire": state.time + (spec.expire or spec.delay),
    }


def _pending_path(entry: dict) -> ReactPath:
    node, arrival_cell, arrival_dir = entry["deferred"]
    return ReactPath(
        endpoint=entry["endpoint"],
        nodes=tuple(tuple(item) for item in entry["nodes"]),
        semantics=frozenset(entry.get("semantics") or ()),
        gated=bool(entry.get("gated")),
        terminal=tuple(entry["cell"]) if entry.get("cell") else None,
        terminal_piece=entry.get("piece"),
        equipment_count=int(entry.get("equipment_count", 0)),
        blank_gated=bool(entry.get("blank_gated")),
        deferred=(tuple(node), tuple(arrival_cell), arrival_dir),
        continuation=tuple(tuple(node) for node in entry.get('continuation', ())),
        output_conditions=tuple((tuple(node), bool(wet), bool(low))
                                for node, wet, low in entry.get('output_conditions', ())),
    )


def _pending_event(state, entry: dict) -> RootEvent:
    data = entry.get("event") or {}
    cell, previous = data.get("cell"), data.get("previous_cell")
    return RootEvent(
        endpoint=entry["endpoint"],
        action_id=int(data.get("action_id", state.time)),
        cell=tuple(cell) if cell else None,
        previous_cell=tuple(previous) if previous else None,
        material=str(data.get("material", "")),
        damage_kind=str(data.get("damage_kind", "")),
        derived=True,
        budget=int(entry.get("budget", FEEDBACK_PER_EVENT)),
    )


def _store_pending(state, path: ReactPath, event: RootEvent) -> FeedbackResult | None:
    """留声片：把这次事件存下来，delay 个客观回合后从存点续走。

    同一插片最多留一个，后来的事件**不覆盖**先存的（§5.4）；全盘最多
    MAX_PENDING 个待释放脉冲。存不下时不扣费、不写冷却。
    """
    piece_id = path.terminal_piece or ""
    if _path_blocked(state, path, event):
        return None
    cell = list(path.terminal or ())
    for entry in state.board_pending:
        if entry.get("piece") == piece_id and list(entry.get("cell") or []) == cell:
            return FeedbackResult(piece_id, False, "留声片已经存着一个事件，不覆盖")
    if len(state.board_pending) >= MAX_PENDING:
        return FeedbackResult(piece_id, False, "待释放脉冲已满")
    record = _pending_record(state, path, event)
    state.board_pending.append(record)
    # 存脉冲也是一次「新增反馈」，同样吃全盘每回合 1 次的预算——否则
    # 留声片会变成绕过预算的第二条免费通道。它自身不另收想象力。
    state.board_feedback_round += 1
    result = FeedbackResult(piece_id, True, detail={"due": record["due"]})
    state.messages.append(_feedback_message(state, piece_id, result))
    return result


def release_pending(state) -> list[FeedbackResult]:
    """留声片到期：从存点接着往下游走一次，按当回合预算结算。

    到期但这一回合预算已被占满时不丢弃——留到下一回合再试，直到过期。
    续走沿用存下时的语义与门状态，不重新采集，也不重新注入根事件端。
    """
    if not state.board_pending:
        return []
    results: list[FeedbackResult] = []
    keep: list[dict] = []
    for entry in state.board_pending:
        if int(entry.get("expire", 0)) < state.time:
            continue
        if int(entry.get("due", 0)) > state.time:
            keep.append(entry)
            continue
        event = _pending_event(state, entry)
        # 每回合名额与**原始根事件**剩下的名额同时生效：延后的脉冲不能因为
        # 换了一回合就把「一次根事件最多 2 次」重新攒满（§5.5）。
        budget = min(event.budget, FEEDBACK_PER_ROUND - state.board_feedback_round)
        if budget <= 0:
            keep.append(entry)
            continue
        fired = 0
        for path in resume_paths(state.board, _pending_path(entry), semantics_of_placement):
            if fired >= budget:
                break
            result = _run_feedback(state, path, event)
            if result is None:
                continue
            results.append(result)
            if result.ok:
                event.budget -= 1
                fired += 1
    state.board_pending = keep
    return results


def emit_root_event(state, endpoint: str, **kwargs) -> list[FeedbackResult]:
    """发出一个根事件并结算线路上合法的派生反馈。

    根事件不携带可执行技能，只携带「发生了什么、在哪里、谁造成、谁承受、
    当时是什么材料」。派生脉冲不能再注入四个根事件端。
    """
    if endpoint not in ENDPOINT_IDS:
        return []
    event = RootEvent(endpoint=endpoint, **kwargs)
    if event.derived:
        return []
    results: list[FeedbackResult] = []
    if not state.board.placements:
        return results
    for path in paths_for(state, endpoint):
        # 两个上限各管各的：每回合 1 次是全局闸门，每事件 2 次只算**成功**的
        # 新增反馈——一条被世界条件挡住的线路不该吃掉整场联想的名额。
        if event.budget <= 0 or state.board_feedback_round >= FEEDBACK_PER_ROUND:
            break
        if path.deferred is not None:
            result = _store_pending(state, path, event)
        else:
            result = _run_feedback(state, path, event)
        if result is not None:
            results.append(result)
            if result.ok:
                event.budget -= 1
    return results


def _feedback_message(state, piece_id: str, result: FeedbackResult) -> str:
    from ..i18n import tr

    label = PIECE_SPECS[piece_id].label
    if piece_id == "spark":
        return tr("联想反馈·{label}：{target} 吃了一记微弱放电（1 点完整度）。",
                  label=tr(label), target=tr(str(result.detail.get("target", ""))))
    if piece_id == "surge":
        return tr("联想反馈·{label}：把 {amount} 单位{kind}涌向相邻格。",
                  label=tr(label), amount=result.detail.get("amount", 0),
                  kind=tr(str(result.detail.get("kind", ""))))
    if piece_id == "ember":
        return tr("联想反馈·{label}：在 {x},{y} 留下一点余温（强度 {strength}）。",
                  label=tr(label), x=(result.detail.get("cell") or (0, 0))[0],
                  y=(result.detail.get("cell") or (0, 0))[1],
                  strength=result.detail.get("strength", EMBER_STRENGTH))
    if piece_id == "voice":
        return tr("联想反馈·{label}：{x},{y} 响起一次轻声（{reached} 个失控意识转头）。",
                  label=tr(label), x=(result.detail.get("cell") or (0, 0))[0],
                  y=(result.detail.get("cell") or (0, 0))[1],
                  reached=result.detail.get("reached", 0))
    if piece_id == "echo_cell":
        return tr("联想反馈·{label}：把这次事件存了下来，{due} 回合时释放。",
                  label=tr(label), due=result.detail.get("due", state.time))
    return tr("联想反馈·{label}：下一次对应创伤减少 1（保留 {until} 回合）。",
              label=tr(label), until=BUFFER_DURATION)


def start_round(state) -> None:
    state.board_feedback_round = 0
    if int(state.board_buffer.get("until", 0)) and state.time > int(state.board_buffer["until"]):
        state.board_buffer = {}
    # 留声片到期的脉冲在回合开头释放：先清预算再放，它才有这一回合的名额。
    release_pending(state)


def prune_on_descend(state) -> None:
    """每次换层清理已不存在的世界目标与待释放坐标；保留玩家级冷却。"""
    state.board_pending = []
    state.board_buffer = {}
    # 接触端去重记录按层作废：新层脚下的材料是一次全新的接触。
    state.board_previous_cell = None
    state.board_touch_cell = None
    state.board_touch_material = ""

