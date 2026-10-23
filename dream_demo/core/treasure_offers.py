"""珍品机会（2026-10-22 A2 P5）：22／24／26 层三批深度的高成本机会。

方案 §6.1：常规 27 层流程在 22—27 层安排**三次**相互独立的高成本珍品机会，
分别覆盖 22—23、24—25、26—27 层；每次从该阶段已开放的 2 件中稳定二选一，
成功后仅得 1 件。机会替换原高价值奖励槽，不额外撒地面物。

因此机会落在每个阶段的**首层**（22／24／26）——该阶段的候选也正是这一层
开放（``min_depth`` 22／24／26）。一局跑完只遇三次这样的选择，六个候选
里恰好拿到三个：每个阶段在两件里挑一件，三段共 2×2×2 种取法。

三条硬口径都在这里：

* **硬下限**——珍品的 ``min_depth``（22／24／26）与本机会的深度一致，
  此前任何渠道都抽不到；本模块只把本阶段的珍品摆出来。
* **始终给没拿过的**——``legal_items`` 走 ``item_access.refusal`` 的统一
  资格查询（``min_depth``／``grant_source``／``run_limit``），拿过的那件
  不会再摆一次。
* **没有合法物时给等价值替代**——本阶段的珍品都拿完时，改摆同档（非常
  稀有）的既有专项物，不给空箱。

机会本体是**事件**（复合事件面板里选），结算走通用事件路径：
``core/actions/social.py::choose_event_option`` 用
``source='event:' + event.event_id`` 发放，正好对上珍品定义里的
``grant_source``（``event:treasure.breach`` 等）。
"""

from __future__ import annotations

from typing import Any

#: 三个阶段的深度带与候选珍品（每阶段两件＝两种战术解法，缺一不可）。
#: ``depth`` 是机会实际落层（= 阶段首层，也是候选开放的层）；``band`` 是
#: 这一机会覆盖的深度带。
TREASURE_STAGES: tuple[dict[str, Any], ...] = (
    {
        "stage": 22,
        "depth": 22,
        "band": (22, 23),
        "event_id": "treasure.breach",
        "catalog_id": "treasure.breach",
        "items": ("breach_spool", "folded_escape_route"),
    },
    {
        "stage": 24,
        "depth": 24,
        "band": (24, 25),
        "event_id": "treasure.storm",
        "catalog_id": "treasure.storm",
        "items": ("storm_accumulator", "quiet_boundary"),
    },
    {
        "stage": 26,
        "depth": 26,
        "band": (26, 27),
        "event_id": "treasure.dawn",
        "catalog_id": "treasure.dawn",
        "items": ("waking_reserve", "bottled_sunrise"),
    },
)

#: 机会本身的崩解度（回应一次就要付，不管拿不拿）。
TREASURE_BASE_DISSOLUTION = 15
#: 取件额外付的崩解度：贵在明面上，放弃则不付。
TREASURE_TAKE_DISSOLUTION = 5
#: 等价值替代的件数（珍品都拿完时摆出来）。
TREASURE_FALLBACK_COUNT = 2


def stage_for_depth(depth: int) -> dict[str, Any] | None:
    """本层有没有珍品机会；在机会层（22／24／26）返回所属阶段。"""
    for stage in TREASURE_STAGES:
        if int(depth) == stage["depth"]:
            return stage
    return None


def stage_for_event(event_id: str) -> dict[str, Any] | None:
    """按事件 id 找回所属阶段。"""
    for stage in TREASURE_STAGES:
        if stage["event_id"] == str(event_id):
            return stage
    return None


def legal_items(state: Any, stage: dict[str, Any]) -> tuple[str, ...]:
    """本阶段还没拿过、且过得了统一资格查询的珍品。

    ``refusal`` 一并管住三件事：梦层下限（本阶段深度带已对齐）、独占渠道
    （``grant_source`` 必须正好是本机会）、本局上限（每件每局最多 1 份）。
    """
    from .item_access import refusal

    source = "event:" + stage["event_id"]
    return tuple(item_id for item_id in stage["items"]
                 if refusal(state, item_id, source=source) is None)


def fallback_items(state: Any, stage: dict[str, Any]) -> tuple[str, ...]:
    """珍品都拿完时的等价值替代：同档（非常稀有）的既有专项物。

    取自通用池、按 id 排序取前若干件——稳定：同一份存档看到的是同一批，
    重开面板、读档都不重抽。``grant_source`` 限死的件过不了资格查询，
    因此不会把别阶段的珍品提前抖落出来。
    """
    from .content import items_of_rarity
    from .item_access import refusal

    source = "event:" + stage["event_id"]
    pool = items_of_rarity("非常稀有", ("易逝物", "摄入物", "交互道具", "携带意象"))
    legal = [item_id for item_id in sorted(pool)
             if refusal(state, item_id, source=source) is None]
    return tuple(legal[:TREASURE_FALLBACK_COUNT])


def build_options(state: Any, stage: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """机会面板的选项：先摆本阶段没拿过的珍品，没有就摆等价值替代。

    选项在**生成时**定死（面板与结算读同一份列表，见篡改规格 §8.1），
    玩家查看、移动、读档都不会让这一批换人。
    """
    options: list[dict[str, Any]] = []
    for item_id in legal_items(state, stage):
        options.append({
            "option_id": f"{stage['event_id']}.take.{item_id}",
            "label": "取走{item}",
            "reward_id": item_id,
            "dissolution": TREASURE_TAKE_DISSOLUTION,
        })
    if not options:
        for item_id in fallback_items(state, stage):
            options.append({
                "option_id": f"{stage['event_id']}.fallback.{item_id}",
                "label": "取走{item}",
                "reward_id": item_id,
                "dissolution": TREASURE_TAKE_DISSOLUTION,
            })
    options.append({"option_id": f"{stage['event_id']}.leave",
                    "label": "不去动它", "leave": True})
    return tuple(options)
