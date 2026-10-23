# -*- coding: utf-8 -*-
"""关键任务对象保护矩阵（docs/噪音与地图篡改改进-2026-10-17.md §二、§四）。

对话篡改只改文本与选项数值；地图篡改会真实抹掉场景里的东西，因此必须回答
一个数据问题：**哪些对象一旦消失，就会让一条任务、一处机关或一扇门永远办不成？**

这里把答案登记成一张矩阵，供 :mod:`dream_demo.core.tamper_protection` 与界面
共用；运行时只做查表与当前状态核对，不解析文案，也不另造一套任务逻辑。

矩阵分五类，来源都是真实定义表（任务、墙种、场景设施），不是手工抄写的名单：

* ``item``     —— 任务交付物与门之钥：删掉就没有第二次获取途径。
* ``liquid``   —— 任务要求的液体种类（例如报童要的幻影墨）：删干／稀释会毁掉交付来源。
* ``threat``   —— 进行中任务绑定的目标实例：删字归因是「环境」而非玩家，
                  直接删掉只会把任务从「击败」降成「确认现场」，等于悄悄毁约。
* ``mechanism``—— 逻辑固体、台子、门与容器：它们承载机关、事件地点与通路；
                  破坏／删除会绕过谜题或把台面上的东西埋进地面。
* ``facility`` —— 场景设施布局覆盖的格：布局格上的固体是设施的一部分，
                  抹掉会让已经排定的条件永久无法满足。
"""

from __future__ import annotations

from .quests import QUEST_DEFINITIONS

#: 跨任务通用的钥匙类物品：唯一来源、丢了不会有第二把。
BASE_KEY_ITEMS: frozenset[str] = frozenset({"door_key"})


def _quest_items() -> frozenset[str]:
    """全部任务定义里以「具名物品」形式要求的交付物。"""
    found: set[str] = set()
    for quest in QUEST_DEFINITIONS.values():
        requirement = quest.get("requirement") or {}
        if requirement.get("type") == "item" and requirement.get("item"):
            found.add(str(requirement["item"]))
    return frozenset(found)


def _quest_liquids() -> frozenset[str]:
    """全部任务定义里以「液体」形式要求的交付物种类。"""
    found: set[str] = set()
    for quest in QUEST_DEFINITIONS.values():
        requirement = quest.get("requirement") or {}
        if requirement.get("type") == "liquid" and requirement.get("liquid"):
            found.add(str(requirement["liquid"]))
    return frozenset(found)


def _quest_delivery_items() -> frozenset[str]:
    """交付给场所的具名物（与 ``requirement`` 分离定义时也收进来）。"""
    found: set[str] = set()
    for quest in QUEST_DEFINITIONS.values():
        delivery = quest.get("delivery_requirement") or {}
        if delivery.get("type") == "item" and delivery.get("item"):
            found.add(str(delivery["item"]))
    return frozenset(found)


#: 任务链依赖的具名物品。
QUEST_KEY_ITEMS: frozenset[str] = BASE_KEY_ITEMS | _quest_items() | _quest_delivery_items()

#: 任务链依赖的液体种类。
QUEST_KEY_LIQUIDS: frozenset[str] = _quest_liquids()


def _mechanism_wall_kinds() -> frozenset[str]:
    """逻辑固体与承载交互的墙种：破坏／删除会绕过机关或埋掉台面内容。"""
    from ..materials.walls import CONTAINER_KINDS, TABLE_KINDS

    return frozenset({
        # 电路逻辑 v2 的触发源／接收器（core/logic.py 的真实现场）。
        "机关石台", "陷阱石台", "感应符文墙", "定时摆轮", "机关门",
        "显影方尖", "囚笼栅栏", "弹射座", "灌注阀", "共鸣报警器",
        # 台面承载事件地点／显化物；容器封存内容物。
        *TABLE_KINDS, *CONTAINER_KINDS,
        # 门是关卡咽喉：删掉等于凭空开路，破坏规则要统一走开门而不是抹墙。
        "门", "木门", "玩具箱门",
    })


#: 不可由篡改破坏／删除的墙种（与 :meth:`GameState._protected_wall` 互为补充）。
MECHANISM_WALL_KINDS: frozenset[str] = _mechanism_wall_kinds()


def matrix_rows() -> tuple[dict[str, object], ...]:
    """玩家可读的矩阵摘要（开发文档／审计脚本共用）。"""
    return (
        {"category": "item", "source": "QUEST_DEFINITIONS.requirement.item",
         "values": tuple(sorted(QUEST_KEY_ITEMS)), "reason_key": "item"},
        {"category": "liquid", "source": "QUEST_DEFINITIONS.requirement.liquid",
         "values": tuple(sorted(QUEST_KEY_LIQUIDS)), "reason_key": "liquid"},
        {"category": "threat", "source": "TaskRecord.target_uid 与进行中任务",
         "values": (), "reason_key": "threat"},
        {"category": "mechanism", "source": "materials.walls 台子／容器／门 + 逻辑固体",
         "values": tuple(sorted(MECHANISM_WALL_KINDS)), "reason_key": "mechanism"},
        {"category": "facility", "source": "world_ledger.facilities.layout",
         "values": (), "reason_key": "facility"},
    )
