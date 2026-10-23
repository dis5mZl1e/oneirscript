"""§9 并发预警名额的公平调度（2026-10-22，A7 剩余项）。

背景：并发预警名额是**遭遇级稀缺资源**——同一场遭遇最多 ``limit`` 只异象
同时蓄力（普通／强烈 2、核心房 3），整层另有硬上限。旧实现在
``EnemySkillMixin._enemy_skill_may_start`` 里直接数「已经有几只同伴在蓄力」，
于是谁能起手只取决于 ``state.enemies`` 的**列表顺序**：

    5 只同遭遇、上限 2 时，第 0／1 只结算完立刻重新起手（同回合内
    它们自己刚结算，pending 已清），第 2—4 只在任何回合都拿不到名额。

本模块只做**纯计算**：不读世界、不写世界、不碰感知。调用方把「谁在等、
从哪个动作序号开始等」交给 :func:`next_grants`，拿回本回合应放行的集合。

规则（对应方案 §9「名额等待按实际就绪／等待时间公平调度」）:

1. **先到先得**——等待起点 ``wait_since`` 越小越优先；
2. **同刻不按列表顺序**——起点相同时按 ``key``（实体稳定标识）排序，
   因此把 ``state.enemies`` 打乱后放行集合不变；
3. **拿到即清零**——放行者由调用方清掉等待起点，下一次从队尾重排，
   名额因此轮转，不会被同一批实体长期占据；
4. **等待人数超过名额时只放前 ``available`` 个**，其余继续等，
   不做「随机挑一个」也不做「全都放」。

公平性的可验证形式（不承诺「每只必中」，只承诺不被饿死）：
``n`` 个竞争者、每回合 ``limit`` 个名额时，任何一只的等待轮数上界是
``ceil(n / limit)``。见 ``tests/test_skill_slot_fairness_261022.py``。
"""

from __future__ import annotations

from typing import Iterable, Sequence


def normalized_key(key: Sequence[object] | str) -> tuple:
    """把实体标识统一成可比较元组（字符串按单元素元组处理）。"""
    if isinstance(key, str):
        return (key,)
    return tuple(key)


def next_grants(
    competitors: Iterable[tuple[Sequence[object] | str, int]],
    available: int,
) -> frozenset:
    """本回合应放行的实体标识集合。

    ``competitors``：``(key, wait_since)`` 序列。``wait_since`` 是**绝对动作
    序号**（``state.action_seq``），不是等待轮数——数越小说明等得越久；
    刚刚就绪的实体传当前 ``action_seq``。

    ``available``：本回合还剩几个名额（已扣掉同遭遇正在蓄力的数量）。
    ``<= 0`` 时返回空集（谁都不放行，等待记录保留）。
    """
    if available <= 0:
        return frozenset()
    ordered = sorted(
        ((normalized_key(key), int(wait), key) for key, wait in competitors),
        key=lambda item: (item[1], item[0]),
    )
    # 回传调用方原本给的标识（不擅自换成归一化元组），便于与实体键直接比较。
    return frozenset(original for _, _, original in ordered[:available])


def starvation_bound(competitors: int, limit: int) -> int:
    """``competitors`` 只争 ``limit`` 个名额时，单只的最大等待轮数。"""
    if limit <= 0:
        return 0
    if competitors <= 0:
        return 0
    return -(-competitors // limit)  # ceil
