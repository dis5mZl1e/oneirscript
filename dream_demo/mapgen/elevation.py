"""平缓地势场：低洼处自然汇液的依据。"""

from __future__ import annotations

import random

def generate_elevation(seed: int, width: int, height: int, cell_size: int = 9) -> list[list[int]]:
    """平缓的地势起伏（0–3）：粗网格随机高度经双线性插值。

    液态记忆的流动按地势差结算，低洼处（低海拔格）更容易自然积液。
    """
    if cell_size < 2:
        raise ValueError("地势网格尺寸必须至少为 2")
    rng = random.Random(seed ^ 0xE1E7A7)
    columns = width // cell_size + 2
    rows = height // cell_size + 2
    coarse = [[rng.choice((0, 1, 1, 2, 2, 3)) for _ in range(columns)] for _ in range(rows)]
    grid = [[0] * width for _ in range(height)]
    for y in range(height):
        gy, fy = divmod(y, cell_size)
        for x in range(width):
            gx, fx = divmod(x, cell_size)
            top_left = coarse[gy][gx]
            top_right = coarse[gy][gx + 1]
            bottom_left = coarse[gy + 1][gx]
            bottom_right = coarse[gy + 1][gx + 1]
            top = top_left + (top_right - top_left) * fx / cell_size
            bottom = bottom_left + (bottom_right - bottom_left) * fx / cell_size
            grid[y][x] = round(top + (bottom - top) * fy / cell_size)
    return grid
