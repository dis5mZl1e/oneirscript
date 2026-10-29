"""CY-5：地图栅格增量内核（逐格 token 计算与脏格筛选）。

只接管「遍历场景格 → 计算内容 token → 与旧 token 比较」的循环；真正的
像素粘贴仍由 Python 侧的 ``_paste_cell`` 回调完成（PIL 调用不受 Cython 影响）。
"""
from __future__ import annotations


def _token(cell, visual, background, fog_background, effect, layers, protected):
    return (cell, visual, background, fog_background, effect,
            getattr(effect[0], 'raster_scale', None) if effect else None,
            layers, bool(protected))


def update_cells(cells, visuals, viewport, backgrounds, effect_glyphs,
                 fog_backgrounds, glyph_layers, protected_cells, previous,
                 paste, cov=None, strict_inside=False):
    """返回 (tokens, inside, painted)。

    ``cov`` 非空时只信任重叠区内未变的 token（平移增量）；
    ``strict_inside`` 专供平移：有格落在视口外即返回 ``None``，由调用方回退。
    """
    left, top, width, height = viewport
    inside = True
    painted = 0
    # 原地更新调用方的 token 表：_update 用自身缓存，_pan 传入的已经是副本。
    tokens = previous
    for pos, cell in cells.items():
        x, y = pos
        if not (left <= x < left+width and top <= y < top+height):
            if strict_inside:
                return None, False, painted
            inside = False
        visual = visuals.get(pos)
        effect = effect_glyphs.get(pos)
        token = _token(cell, visual, backgrounds.get(pos), fog_backgrounds.get(pos),
                       effect, glyph_layers.get(pos), pos in protected_cells)
        if cov is not None:
            cov_left, cov_top, cov_right, cov_bottom = cov
            unchanged = (cov_left <= x < cov_right and cov_top <= y < cov_bottom
                         and previous.get(pos) == token)
        else:
            unchanged = previous.get(pos) == token
        if unchanged:
            continue
        tokens[pos] = token
        paste(pos, cell, visual, token)
        painted += 1
    return tokens, inside, painted
