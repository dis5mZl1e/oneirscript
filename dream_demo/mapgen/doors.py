"""门位放置：把 1 格宽通道里的若干格指定为「门」。"""

from __future__ import annotations

import random

from .layout import normalize_map_form

def place_doors(
    solid_mask: list[list[bool]],
    seed: int,
    width: int,
    height: int,
    map_form: str = "整齐的房间",
) -> set[tuple[int, int]]:
    """在 1 格宽通道上撒门：挑选「1 格宽通道里的开放格」作为门位。

    这些开放格由 ``_generate_cells`` 先变成实心、再经 ``_assign_wall_kinds`` 染成
    「门」墙种（高墙、恒阻视线、踏上即开），成为关卡里可开合的咽喉点：关闭时
    挡路，生物/物品踩上即开。门位即 1 格宽通道里的格子——左右（或上下）为开放
    地面、而上下（或左右）为实心墙。不同层型给不同密度：走廊/迷宫类通道极多，
    密度压低；房间类适度。用种子随机抽一部分，避免把每条通道都变成门。
    """
    form = normalize_map_form(map_form)
    density = {
        "整齐的房间": 0.21,
        "破碎的房间": 0.19,
        "居民区": 0.23,
        "洞穴": 0.35,
        "迷宫": 0.10,
        "长廊": 0.19,
        "无限房间": 0.35,
        "碎影平原": 0.35,
        "回声大厅": 0.25,
    }.get(form, 0.20)

    candidates: list[tuple[int, int]] = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if solid_mask[y][x]:
                continue
            open_lr = (not solid_mask[y][x - 1]) and (not solid_mask[y][x + 1])
            solid_ud = solid_mask[y - 1][x] and solid_mask[y + 1][x]
            open_ud = (not solid_mask[y - 1][x]) and (not solid_mask[y + 1][x])
            solid_lr = solid_mask[y][x - 1] and solid_mask[y][x + 1]
            if (open_lr and solid_ud) or (open_ud and solid_lr):
                candidates.append((x, y))
    rng = random.Random(seed ^ 0x5D00D)
    rng.shuffle(candidates)
    # 5×5 隔离：任何两扇门不得落在彼此切比雪夫距离 2 以内
    # （一条窄通道连续几格都是候选时，只保留其中一扇门）。
    spaced: list[tuple[int, int]] = []
    for candidate in candidates:
        if all(
            max(abs(candidate[0] - placed[0]), abs(candidate[1] - placed[1])) > 2
            for placed in spaced
        ):
            spaced.append(candidate)
    count = int(len(spaced) * density)
    # 兜底上限，避免超大门厅变成满墙门：
    cap = max(3, (width * height) // 45)
    count = min(count, cap)
    return set(spaced[:count])
