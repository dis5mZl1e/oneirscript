"""稳定 ID 派生（重构方案 §13.2：记账一律用 ID，不用坐标／翻译文本／按钮序号）。

对话选项过去只有「显示下标」可用：货架抽 2–3 项、``show_if`` 再过滤一层，
同一个下标在任务状态变化前后会指向不同选项，一次性交易的记账因此会串。
这里的 ID 由**定义表位置**与选项自身的语义字段派生，与展示顺序无关：

* 任务、赠品、位面入口、谜题一类有语义锚点的选项 → 用锚点当 ID
  （``npc.scrap_registrar.accept.quest.pump_hunt``），表内重排也不会改号；
* 纯货架交易 → 用定义表序号（``npc.scrapper.trade.2``）。

数据里可以显式写 ``option_id`` 覆盖派生结果；校验只要求同一职业内唯一。
"""

from __future__ import annotations

from typing import Any, Mapping
from zlib import crc32

#: 有语义锚点的字段 → ID 片段前缀。按顺序取第一个命中的。
_ANCHORS: tuple[tuple[str, str], ...] = (
    ("accept_quest", "accept"),
    ("complete_quest", "deliver"),
    ("gift_set", "gift"),
    ("enter_realm", "enter"),
    ("deep_dialogue", "deep"),
    ("puzzle", "puzzle"),
    ("scene_command", "scene"),
    ("service", "service"),
)


def npc_option_id(npc_kind: str, position: int, option: Mapping[str, Any]) -> str:
    """一名稳定意识的某个对话选项的稳定 ID。"""
    explicit = option.get("option_id")
    if explicit:
        return str(explicit)
    for field, prefix in _ANCHORS:
        if option.get(field):
            if field == "gift_set":
                # 一组赠品可以摆好几件供选（「一件为限」靠 gift_set 记账），
                # 所以 ID 要带上表内位置，否则同一组的几个选项会互相顶掉。
                return f"{npc_kind}.{prefix}.{option[field]}.{position}"
            if field == "complete_quest" and option.get("reward"):
                # 同一单可以摆出几档报酬：报酬键是这一项语义的一部分，不带就会把
                # 两份销账记成同一笔一次性交易。
                return f"{npc_kind}.{prefix}.{option[field]}.{option['reward']}"
            return f"{npc_kind}.{prefix}.{option[field]}"
    if option.get("leave"):
        return f"{npc_kind}.leave"
    if option.get("circuit_hint"):
        return f"{npc_kind}.circuit_hint"
    if option.get("cost") or option.get("gain"):
        return f"{npc_kind}.trade.{position}"
    return f"{npc_kind}.talk.{position}"


def event_definition_id(event_id: str) -> str:
    """Strip the generator's coordinate suffix while preserving authored IDs."""
    base, separator, suffix = str(event_id).rpartition('@')
    coordinates = suffix.split(',')
    if separator and len(coordinates) == 2 and all(part.lstrip('-').isdigit() for part in coordinates):
        return base
    return str(event_id)


def event_option_id(event_id: str, position: int, option: Mapping[str, Any]) -> str:
    """一个事件选项的稳定 ID（事件表是元组，序号即定义表位置）。"""
    explicit = option.get("option_id")
    if explicit:
        return str(explicit)
    event_id = event_definition_id(event_id)
    if option.get("leave"):
        return f"{event_id}.leave"
    for field, prefix in _ANCHORS:
        if option.get(field):
            return f"{event_id}.{prefix}.{option[field]}"
    return f"{event_id}.option.{position}"


def npc_option_ids(npc_kind: str, options: Any) -> tuple[str, ...]:
    return tuple(npc_option_id(npc_kind, index, option) for index, option in enumerate(options or ()))


def stable_seed(*parts: Any) -> int:
    """把若干稳定 ID 折成一个跨进程一致的 32 位整数，供 ``random.Random`` 播种。

    用 ``zlib.crc32`` 而不是内建 ``hash``：后者对字符串带随机盐，同一笔交易在
    两次运行里会抽到不同结果，数值锁定与回放探针都会因此失准。
    """
    digest = 0
    for part in parts:
        digest = crc32(str(part).encode("utf-8") + b"\x1f", digest)
    return digest
