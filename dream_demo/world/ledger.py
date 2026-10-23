"""世界记录（重构方案 §12.2）：独立于层快照的身份、设施与地形增量。

层快照（``layer_states``）只保留当前层 ±3 的窗口，窗口外的层按种子重建。
重建会重新铸造实例 id、重新抽签货架，所以任何「谁在这儿、这台设施还剩几次、
这格被永久改成了什么」的事实都不能存在快照里——否则远层回来就又能领一次奖。

这里存的是那部分必须活得比快照久的记录：

* :class:`ActorRecord` —— 跨层稳定的角色身份与行程（§6.3）。
* :class:`FacilityRecord` —— 场景设施的状态、余量与冷却（§10.2）。
* :class:`TaskRecord` —— 任务实例：绑定的目标 UID、接取时刻与已成立的解法（§7.1）。
* ``terrain`` —— 结构性改造的**必要格子增量**，按地点键回放到重建后的地图。
* ``facts`` —— 有限长度行动事实 + 永久保留的重要关系事实（§13.3）。

一次性收益的记账（``npc_traded_options``/``gift_claims``）目前仍按 ``actor_uid ×
option_id`` 存在 GameState 上（P0 落地），等 ``world/transactions.py`` 接管报价
库存时再迁到这里，不并行维护两套真相。

不保存无界历史：普通事实只留最近 ``FACT_WINDOW`` 条，重要种类（警告、契约、
结算）单独留下，因为它们要支撑之后的责任归属与声望结算。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

#: 只描述「谁此刻站在哪」的事实量很大，且过几层就没人再查它们。
FACT_WINDOW = 240
#: 关系与结算事实要跨层生效（§4.4 目击／通报、§7.1 一次性结算键），不裁剪。
PERSISTENT_FACT_KINDS = frozenset({"warn", "conflict", "pact", "settle", "deliver",
                                   "facility", "safety", "report"})


@dataclass
class ActorRecord:
    """一个稳定意识的跨层档案：身份、岗位、立场与行程。

    ``layer_key`` 是它**当前**所在的层；换层时由 :mod:`dream_demo.world.travel`
    更新，一帧内不能同时出现在两层（§12.2「行程更新与旧层移除必须原子执行」）。
    """

    actor_uid: str = ""
    npc_kind: str = ""
    home_layer_key: str = ""
    layer_key: str = ""
    x: int = 0
    y: int = 0
    stance: str = "中立"
    behavior: str = "岗位"
    alive: bool = True
    important: bool = False
    itinerary: tuple[str, ...] = ()
    next_stop: str = ""
    travel_stage: str = ""
    # 货架抽签结果：抽过一次就是这一位终身的摊位，重进地图／远层重建都不重抽。
    shelf: tuple[int, ...] = ()
    # ---- 立场机（§4.4）：以上身份字段之外，只有这几项记「关系现在到哪一步」----
    # 当前立场开始的世界时刻：冷静期（8 回合）与警告失效期（6 回合）都读它，
    # 用世界时刻而不是回合计数，亚回合行动不会假装时间走过了一整回合。
    stance_since: int = 0
    # 最近一次「可归属的轻微侵害」的来源标识与时刻：警告后同源再犯才升级严重冲突。
    last_grievance: str = ""
    last_grievance_time: int = 0
    # 停战后开出的补偿要价（§4.4「提出补偿 → 支付并履约」）。
    restitution: int = 0


@dataclass
class FacilityRecord:
    """一处场景设施的持久状态（§10.2）。

    ``state`` 是定义表声明的状态名（如 ``未开启/等待支付/开启/已关闭``）；
    ``stock``/``uses_left`` 记剩余燃料、次数等有界资源；``cooldown_until`` 用
    世界时间而不是回合计数，这样亚回合行动不会假装冷却走过了一整回合。
    """

    definition_id: str = ""
    scene_uid: str = ""
    layer_key: str = ""
    anchor_uid: str = ""
    state: str = ""
    stock: dict[str, int] = field(default_factory=dict)
    uses_left: int = 0
    cooldown_until: int = 0
    partners: tuple[str, ...] = ()
    # 绝对坐标布局（锚点/边槽/作用区/排放区）：随设施一起持久化，远层重建后
    # 仍然指着同一批格子；地形增量另外记在 ``terrain`` 里回放。
    layout: dict[str, Any] = field(default_factory=dict)
    # 同一设施内「逐格分别成立」的开关（§9 R04 两端要分别激活）。布局键 → 是否成立；
    # 放在记录里而不是 stock，才不会把「已经立住的折页」当成一份可消耗的储量记账。
    flags: dict[str, bool] = field(default_factory=dict)
    # 连续安全的**世界回合**起点：布局键 → 从第几回合起一直没断（§7.2「保持泵房安全
    # 3 回合」）。断一次就整条删掉、从当前回合重新数；达成后另记一条 safety 事实。
    safe_since: dict[str, int] = field(default_factory=dict)
    # 已排定的延迟效果（§10.2「新建立的伤害场先显示预告」）：``due_seq`` 之后的
    # 第一个**实际**玩家行动才落地。
    pending: dict[str, Any] = field(default_factory=dict)

    def ready(self, world_time: int) -> bool:
        return world_time >= self.cooldown_until

    def cell(self, key: str) -> tuple[int, int] | None:
        """单格布局键；存档往返后 tuple 会变成 list，这里统一读回坐标。"""
        entry = self.layout.get(key)
        if (isinstance(entry, (list, tuple)) and len(entry) == 2
                and all(isinstance(value, int) for value in entry)):
            return (int(entry[0]), int(entry[1]))
        return None

    def area(self, key: str) -> tuple[tuple[int, int], ...]:
        """作用区／边槽一类「多格」布局键，统一读成坐标元组。"""
        entry = self.layout.get(key) or ()
        if (isinstance(entry, (list, tuple)) and len(entry) == 2
                and all(isinstance(value, int) for value in entry)):
            return ((int(entry[0]), int(entry[1])),)
        out: list[tuple[int, int]] = []
        for item in entry:
            if (isinstance(item, (list, tuple)) and len(item) == 2
                    and all(isinstance(value, int) for value in item)):
                out.append((int(item[0]), int(item[1])))
        return tuple(out)

    def spend(self, name: str, amount: int) -> int:
        """扣一笔库存，返回**实际**扣掉的量（不足额时按剩余额截断）。"""
        left = max(0, int(self.stock.get(name, 0)))
        taken = min(left, amount)
        self.stock[name] = left - taken
        return taken


@dataclass
class TaskRecord:
    """一个任务实例（§7.1）：定义 ID 与实例 UID 分离，进度只认接取之后的事实。

    ``target_uid``／``site_uid`` 指向地图上真实存在的目标与场所，所以「办没办成」
    由行动事实回答，而不是由整局计数器代替（§7.3）。``resolution`` 记的是**哪一条
    允许的解法**成立（击败／诱离封守／确认现场），报酬据此给。
    """

    task_uid: str = ""
    definition_id: str = ""
    giver_uid: str = ""
    target_uid: str = ""
    site_uid: str = ""
    layer_key: str = ""
    # 接取瞬间的世界事实序号与世界回合：此后的一切进度都以此为界（§7.3）。
    # 用事实序号而不是行动序号：行动序号要到一次行动**结算完**才 +1，同一次行动里
    # 先杀后接与先接后杀会落在同一个数上，「接取之前不计」就守不住了。
    accepted_mark: int = 0
    accepted_time: int = 0
    resolution: str = ""
    status: str = "进行中"
    reward: str = ""
    failure: str = ""


@dataclass
class WorldLedger:
    run_uid: str = ""
    actors: dict[str, ActorRecord] = field(default_factory=dict)
    facilities: dict[str, FacilityRecord] = field(default_factory=dict)
    # 任务实例：与设施同类，必须活得比层快照久——远层回来时「这一单已经接过、
    # 绑的是哪一位」不能重算一遍。
    tasks: dict[str, TaskRecord] = field(default_factory=dict)
    # layer_key → {"x,y": 字段名→值}：结构性改造只存被改动的格子。
    terrain: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    facts: list[dict[str, Any]] = field(default_factory=list)
    # 已结算过的任务实例，防止「回旧层再交一次」（§7.1 一次性结算键）。
    settled_tasks: dict[str, str] = field(default_factory=dict)
    # 派系声望（§4.3）：faction_id → {"value": int, "once_keys": {结算键: True}}。
    # 与立场平级：立场管单个对象的态度，声望管一群人的服务账本；都是本局数据，
    # 活得比层快照久。once_keys 是「同一任务实例只改变一次声望」的账。
    reputations: dict[str, dict[str, Any]] = field(default_factory=dict)
    seq: int = 0

    # ------------------------------------------------------------- 角色

    def register(self, record: ActorRecord) -> ActorRecord:
        """登记（或就地更新）一个角色：同一 actor_uid 全局只有一个实例。"""
        existing = self.actors.get(record.actor_uid)
        if existing is None:
            self.actors[record.actor_uid] = record
            return record
        existing.npc_kind = record.npc_kind or existing.npc_kind
        existing.home_layer_key = existing.home_layer_key or record.home_layer_key
        return existing

    def actor(self, actor_uid: str) -> ActorRecord | None:
        return self.actors.get(actor_uid)

    def actors_on(self, layer_key: str) -> list[ActorRecord]:
        return [record for record in self.actors.values()
                if record.layer_key == layer_key and record.alive]

    def move(self, actor_uid: str, layer_key: str, *, x: int | None = None,
             y: int | None = None) -> bool:
        """把角色整体迁到另一层：旧层记录同时失效，不会出现「两层各有一份」。"""
        record = self.actors.get(actor_uid)
        if record is None or record.layer_key == layer_key:
            return False
        record.layer_key = layer_key
        if x is not None:
            record.x = x
        if y is not None:
            record.y = y
        return True

    # ------------------------------------------------------------- 设施

    def facility(self, scene_uid: str, *, layer_key: str = "", anchor_uid: str = "",
                 state: str = "", uses_left: int = 0, definition_id: str = "",
                 stock: Iterable[tuple[str, int]] = ()) -> FacilityRecord:
        record = self.facilities.get(scene_uid)
        if record is None:
            record = FacilityRecord(scene_uid=scene_uid, layer_key=layer_key,
                                    anchor_uid=anchor_uid, state=state,
                                    uses_left=uses_left, stock=dict(stock),
                                    definition_id=definition_id)
            self.facilities[scene_uid] = record
        return record

    # ------------------------------------------------------------- 任务

    def task(self, task_uid: str, definition_id: str, *, npc: str = "",
             target_uid: str = "", site_uid: str = "", layer_key: str = "",
             accepted_mark: int = 0, accepted_time: int = 0) -> TaskRecord:
        """取（或建）一个任务实例：同一 ``task_uid`` 全局只有一份。"""
        record = self.tasks.get(task_uid)
        if record is None:
            record = TaskRecord(task_uid=task_uid, definition_id=definition_id,
                                giver_uid=npc, target_uid=target_uid,
                                site_uid=site_uid, layer_key=layer_key,
                                accepted_mark=accepted_mark, accepted_time=accepted_time)
            self.tasks[task_uid] = record
        return record

    # ------------------------------------------------------------- 地形

    def mark_terrain(self, layer_key: str, x: int, y: int, **fields: Any) -> None:
        """记住一格的结构性改动，重建该层后回放（§12.2）。"""
        self.terrain.setdefault(layer_key, {})[f"{x},{y}"] = {
            key: (list(value) if isinstance(value, (list, tuple)) else value)
            for key, value in fields.items()
        }

    def terrain_for(self, layer_key: str) -> dict[str, dict[str, Any]]:
        return self.terrain.get(layer_key, {})

    # ------------------------------------------------------------- 事实

    def add_fact(self, fact: dict[str, Any]) -> None:
        self.facts.append(fact)
        if len(self.facts) > FACT_WINDOW:
            # 只丢最旧的「瞬时」事实，重要事实往后挪一位继续留着。
            for index, entry in enumerate(self.facts):
                if entry.get("kind") not in PERSISTENT_FACT_KINDS:
                    del self.facts[index]
                    break
            else:
                del self.facts[0]

    def facts_where(self, **filters: Any) -> list[dict[str, Any]]:
        """按字段过滤事实（任务归属、关系证据都走这里，不各自翻历史）。"""
        wanted = {key: value for key, value in filters.items() if value is not None}
        return [entry for entry in self.facts
                if all(entry.get(key) == value for key, value in wanted.items())]

    def has_settled(self, task_uid: str) -> bool:
        return task_uid in self.settled_tasks

    # ------------------------------------------------------------- 存档

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_uid": self.run_uid,
            "seq": self.seq,
            "actors": {uid: asdict(record) for uid, record in self.actors.items()},
            "facilities": {uid: asdict(record) for uid, record in self.facilities.items()},
            "tasks": {uid: asdict(record) for uid, record in self.tasks.items()},
            "terrain": self.terrain,
            "facts": self.facts,
            "settled_tasks": self.settled_tasks,
            "reputations": self.reputations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldLedger":
        ledger = cls(run_uid=str(data.get("run_uid", "") or ""),
                     seq=int(data.get("seq", 0) or 0),
                     terrain={str(key): {str(cell): dict(fields or {})
                                         for cell, fields in (cells or {}).items()}
                              for key, cells in (data.get("terrain") or {}).items()},
                     facts=[dict(entry) for entry in (data.get("facts") or [])],
                     settled_tasks={str(k): str(v)
                                    for k, v in (data.get("settled_tasks") or {}).items()})
        for fid, raw in (data.get("reputations") or {}).items():
            payload = dict(raw or {})
            ledger.reputations[str(fid)] = {
                "value": int(payload.get("value", 0) or 0),
                "once_keys": {str(k): True for k in (payload.get("once_keys") or {})},
            }
        for uid, raw in (data.get("actors") or {}).items():
            payload = dict(raw)
            payload["itinerary"] = tuple(payload.get("itinerary") or ())
            payload["shelf"] = tuple(payload.get("shelf") or ())
            ledger.actors[str(uid)] = ActorRecord(**{key: value for key, value in payload.items()
                                                    if key in ActorRecord.__dataclass_fields__})
        for uid, raw in (data.get("facilities") or {}).items():
            payload = dict(raw)
            payload["partners"] = tuple(payload.get("partners") or ())
            payload["stock"] = {str(k): int(v) for k, v in (payload.get("stock") or {}).items()}
            payload["flags"] = {str(k): bool(v) for k, v in (payload.get("flags") or {}).items()}
            payload["safe_since"] = {str(k): int(v)
                                     for k, v in (payload.get("safe_since") or {}).items()}
            ledger.facilities[str(uid)] = FacilityRecord(
                **{key: value for key, value in payload.items()
                   if key in FacilityRecord.__dataclass_fields__})
        for uid, raw in (data.get("tasks") or {}).items():
            ledger.tasks[str(uid)] = TaskRecord(
                **{key: value for key, value in dict(raw).items()
                   if key in TaskRecord.__dataclass_fields__})
        return ledger
