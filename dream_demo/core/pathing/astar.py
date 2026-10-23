"""通用 8 向 A* 寻路核心。

只做一件事：在 ``width × height`` 的网格上，从 ``start`` 到 ``target`` 找
最短路。地形可通行性由调用方给的 ``passable(x, y)`` 决定，额外的不可穿越
格子（生物、玩家等）由 ``blocked`` 集合给出——目标格永远允许被「抵达」
（用于接近攻击），即使它在 ``blocked`` 里。

斜向与直向同价（1 格 1 步，与 move_player 一致），启发式取切比雪夫距离
（单位代价下的精确下界，保证最优）。返回值不含起点；不可达返回 []。
"""

from __future__ import annotations

import heapq

_DIAGONAL_STEPS = ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1))


def find_path(
    width: int,
    height: int,
    start: tuple[int, int],
    target: tuple[int, int],
    passable,
    blocked: frozenset[tuple[int, int]] | set[tuple[int, int]] = frozenset(),
    *, diagonal: bool = True, landing=None, step_cost=None,
) -> list[tuple[int, int]]:
    """8 向 A* 最短路；返回不含 ``start`` 的格子序列，不可达为空表。

    ``passable(x, y)`` 判定地形可通行（门、征兆绕行等规则由调用方封装）；
    ``blocked`` 里的格子不可穿越，但 ``target`` 本身例外（允许路径终止在
    被占据的目标格上，供「接近后攻击」使用）。

    **性能（2026-09-17 优化）**：辅助瞄准/目标辅助会在鼠标每次掠过时重算，
    1 宽通道与远处目标下原实现单次可达 5–10ms（悬停在墙格时目标不可达，A*
    会搜完整个可达区才返回空）。三处改动把这条路压下来：

    1. **目标格先判可通行**：目标本身走不进去（墙格）时立刻返回空表，
       不再做整图搜索——鼠标掠过墙体是最常见的情形；
    2. **可通行性记忆**：同一格只问一次 ``passable``（8 邻域会重复询问，
       实测调用数降到约 1/4）；
    3. **h 作次级比较键**：f 相同时优先扩展离目标更近的格子（不改 f 的
       优先级，仍是同价下的最短路），等 f 的“平原”不再被整片摊开。
    """
    if not (0 <= target[0] < width and 0 <= target[1] < height):
        return []
    if not (0 <= start[0] < width and 0 <= start[1] < height):
        return []
    if start == target:
        return []
    target_x, target_y = target
    # ① 目标格不可通行（墙体等）→ 无路可走。放在最前面，省掉整图搜索。
    if target not in blocked and not passable(target_x, target_y):
        return []

    memo: dict[tuple[int, int], bool] = {start: True}

    def is_passable(x: int, y: int) -> bool:
        cell = (x, y)
        known = memo.get(cell)
        if known is None:
            known = memo[cell] = bool(passable(x, y))
        return known

    # 堆项 = (f, h, cost, counter, 格)：f 优先，h 作次级键（同 f 时先扩更近目标的），
    # counter 保证同优先级时比较不落到元组（格）比较上、也避免堆项互相比较。
    start_h = max(abs(target_x - start[0]), abs(target_y - start[1]))
    frontier: list[tuple[int, int, int, int, tuple[int, int]]] = [(start_h, start_h, 0, 0, start)]
    best_cost: dict[tuple[int, int], int] = {start: 0}
    previous: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    counter = 0
    push = heapq.heappush
    pop = heapq.heappop
    while frontier:
        _, _, cost, _, current = pop(frontier)
        if cost > best_cost[current]:
            continue  # 过期堆项：该格已用更低代价展开过。
        if current == target:
            break
        x, y = current
        for dx, dy in (_DIAGONAL_STEPS if diagonal else _DIAGONAL_STEPS[:4]):
            nx = x + dx
            ny = y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            neighbor = (nx, ny)
            if not is_passable(nx, ny) or (neighbor != target and neighbor in blocked):
                continue
            if landing is not None:
                neighbor = landing(x, y, dx, dy)
                nx, ny = neighbor
            next_cost = cost + (step_cost(nx, ny) if step_cost is not None else 1)
            known = best_cost.get(neighbor)
            if known is not None and known <= next_cost:
                continue
            if not is_passable(nx, ny):
                continue
            if neighbor != target and neighbor in blocked:
                continue
            best_cost[neighbor] = next_cost
            previous[neighbor] = current
            counter += 1
            heuristic = target_x - nx
            if heuristic < 0:
                heuristic = -heuristic
            vertical = target_y - ny
            if vertical < 0:
                vertical = -vertical
            if vertical > heuristic:
                heuristic = vertical
            if landing is not None or step_cost is not None:
                heuristic = 0  # 滑行/加权步不能把普通距离当步数下界。
            push(frontier, (next_cost + heuristic, heuristic, next_cost, counter, neighbor))
    if target not in previous:
        return []
    path: list[tuple[int, int]] = []
    cursor: tuple[int, int] | None = target
    while cursor and cursor != start:
        path.append(cursor)
        cursor = previous[cursor]
    path.reverse()
    return path
