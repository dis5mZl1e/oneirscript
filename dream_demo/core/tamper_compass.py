
"""篡改句子的方位与对象指代（2026-10-18 docs 第 8 节第二批）。

方向规则（docs §8.4）：
- 固定地图方向：北 = 地图上方，不随角色朝向旋转；八方向按夹角划分；
- 脚下对象单独称「脚下」；
- 方位在打开草稿时确定，随 WorldSlot.reference 固定；查看地图只移动观察
  光标，不改变玩家位置，因此不改变方位参照；
- 身份使用稳定的对象引用（WorldSlot.enemy / 坐标），显示文本不参与查找；
- 同名异象跨方位用方位区分；同方位多只再分近处/远处，仍不能区分时用稳定
  编号（①②…，仅限本次草稿，按距离与坐标排序，不随面板刷新跳号）。
"""
from __future__ import annotations

import math
from typing import Any, Iterable

from ..i18n import tr

# 角度扇区：0°=东，逆时针为正（屏幕上方为北）。顺序从正北开始便于稳定排序。
_SECTOR_NAMES = ("北", "东北", "东", "东南", "南", "西南", "西", "西北")
_SECTOR_ORDER = {name: index for index, name in enumerate(_SECTOR_NAMES)}
_NUMBERS = "①②③④⑤⑥⑦⑧⑨⑩"


def _sector(dx: int, dy: int) -> str:
    if dx == 0 and dy == 0:
        return ""
    angle = math.degrees(math.atan2(-dy, dx)) % 360
    index = int((angle + 22.5) // 45) % 8
    # index 0=东；转到以正北为 0 的顺序。
    return ("东", "东北", "北", "西北", "西", "西南", "南", "东南")[index]


def direction_label(dx: int, dy: int) -> str:
    """八方向名（含「侧」）；同格返回「脚下」。"""
    sector = _sector(dx, dy)
    if not sector:
        return tr("脚下")
    return tr("{direction}侧", direction=tr(sector))


def direction_of(state: Any, x: int, y: int) -> str:
    return direction_label(int(x) - state.player.x, int(y) - state.player.y)


def _number(index: int) -> str:
    return _NUMBERS[index] if index < len(_NUMBERS) else str(index + 1)


def _sort_key(slot: Any) -> tuple:
    direction = slot.direction.replace("侧", "").replace(tr("脚下"), "北")
    return (_SECTOR_ORDER.get(direction, 9), int(slot.distance), int(slot.x), int(slot.y))


def enrich_slots(state: Any, slots: Iterable[Any]) -> None:
    """为槽位写入方位/距离/显示引用；就地修改。"""
    slots = list(slots)
    for slot in slots:
        slot.distance = max(abs(int(slot.x) - state.player.x),
                            abs(int(slot.y) - state.player.y))
        slot.direction = direction_of(state, slot.x, slot.y)
        slot.number = 0

    anomalies = [slot for slot in slots if slot.category == "anomaly"]
    groups: dict[str, list[Any]] = {}
    for slot in anomalies:
        groups.setdefault(slot.label, []).append(slot)
    for name, group in groups.items():
        for slot in group:
            if len(group) == 1:
                slot.reference = tr("{direction}的{name}", direction=slot.direction, name=name)
        if len(group) == 1:
            continue
        by_direction: dict[str, list[Any]] = {}
        for slot in group:
            by_direction.setdefault(slot.direction, []).append(slot)
        for direction, same_direction in by_direction.items():
            same_direction.sort(key=_sort_key)
            if len(same_direction) == 1:
                same_direction[0].reference = tr(
                    "{direction}的{name}", direction=direction, name=name)
                continue
            distances = [slot.distance for slot in same_direction]
            if len(same_direction) == 2 and distances[0] != distances[1]:
                near, far = sorted(same_direction, key=_sort_key)
                near.reference = tr("{direction}近处的{name}", direction=direction, name=name)
                far.reference = tr("{direction}远处的{name}", direction=direction, name=name)
                continue
            for index, slot in enumerate(same_direction):
                slot.number = index + 1
                slot.reference = tr("{direction}{number}号{name}", direction=direction,
                                    number=_number(index), name=name)

    # 非异象同名对象：显示上也按方位/编号区分（身份仍是各自的坐标）。
    others: dict[str, list[Any]] = {}
    for slot in slots:
        if slot.category == "anomaly":
            continue
        others.setdefault(slot.label, []).append(slot)
    for name, group in others.items():
        if all(getattr(slot, "region_kind", "") for slot in group):
            # 区域槽的显示引用已在收集阶段按成员跨方位生成（可能「北侧至东北侧」），
            # 不能被锚点单格方位覆盖；身份仍由物态+材料+成员集合决定。
            continue
        if len(group) == 1:
            group[0].reference = tr("{direction}的{name}",
                                    direction=group[0].direction, name=name)
            continue
        by_direction: dict[str, list[Any]] = {}
        for slot in group:
            by_direction.setdefault(slot.direction, []).append(slot)
        for direction, same_direction in by_direction.items():
            same_direction.sort(key=_sort_key)
            if len(same_direction) == 1:
                same_direction[0].reference = tr(
                    "{direction}的{name}", direction=direction, name=name)
                continue
            for index, slot in enumerate(same_direction):
                slot.number = index + 1
                slot.reference = tr("{direction}第{number}处{name}", direction=direction,
                                    number=_number(index), name=name)

    for slot in slots:
        if not slot.reference:
            slot.reference = slot.label
