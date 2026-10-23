"""Live image map compositor consuming the shared SceneSnapshot (docs §13.4).

Both the WezTerm output and offline samples use this compositor. No renderer
reads the real world: original material colours and actual bundled glyphs come
from a permission-filtered scene. Cell rasters are bounded and cached.
"""
from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

from ..core.map_scene import SceneCell, SceneSnapshot
from ..materials import CONTAINER_KINDS

UNKNOWN = (7, 7, 11)
MEMORY_DIM = 0.42
DEFAULT_GROUND = (42, 42, 54)
SMALL_CELL = 16
ORDINARY_GROUNDS = ("", "普通聚合物", "空白聚合物")


def _hex(value: str, fallback=(80, 80, 96)) -> tuple[int, int, int]:
    value = str(value or "").lstrip("#")
    if len(value) != 6:
        return fallback
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return fallback


def _floor_color(cell: SceneCell, realm_id: str = '') -> tuple[int, int, int]:
    if cell.terrain is None:
        return UNKNOWN
    variant = cell.terrain.aggregate_variant
    try:
        from ..core.realm_surface import FLOOR_COLORS
        explicit = FLOOR_COLORS.get(realm_id, {}).get(variant, '')
        if explicit:
            return _hex(explicit, DEFAULT_GROUND)
    except Exception:
        pass
    try:
        # 主梦层没有专属色表时，用统一材质色作为低亮度地面底，保留地板身份。
        from ..materials import floor_def
        return _hex(floor_def(variant).color, DEFAULT_GROUND)
    except Exception:
        return DEFAULT_GROUND


def _blend(base, top, alpha: float):
    return tuple(int(base[i] * (1 - alpha) + top[i] * alpha) for i in range(3))


def _light_tint(base, lights, x, y, left, top, cw, ch, alpha_scale=1.0):
    """彩色环境光只作用于普通地形，不碰液气/生物/物品等前景信息色。

    ``alpha_scale`` 给墙体用：普通墙只受 8—18% 的光（§12.3.2），比地面收敛，
    连续实心轮廓与墙种识别色仍是主体。
    """
    r, g, b = base
    for lx, ly, radius, color in lights:
        if max(abs(x - lx), abs(y - ly)) > radius:
            continue
        strength = max(0.0, 1.0 - max(abs(x - lx), abs(y - ly)) / max(1.0, radius))
        lr, lg, lb = _hex(str(color), (255, 209, 102))
        alpha = 0.24 * strength * float(alpha_scale)
        r = int(r * (1 - alpha) + lr * alpha)
        g = int(g * (1 - alpha) + lg * alpha)
        b = int(b * (1 - alpha) + lb * alpha)
    return (r, g, b)


def _cell_gradient(draw, base, lights, x, y, px, py, cw, ch):
    """§12 C：格内克制渐变——远离主光源的半格压暗 6%。

    只是把「格间明暗差」补成格内的方向感，不改身份色、不模糊图标；
    液体/气体/火焰/特殊地板调用方已排除。光源太弱（<25%）时不画，
    避免整屏碎块。
    """
    best = None
    best_strength = 0.0
    for lx, ly, radius, _color in lights:
        distance = max(abs(x - lx), abs(y - ly))
        if distance > radius:
            continue
        strength = 1.0 - distance / max(1.0, float(radius))
        if strength > best_strength:
            best_strength = strength
            best = (lx, ly)
    if best is None or best_strength < 0.25:
        return
    dx = 0 if best[0] == x else (1 if best[0] > x else -1)
    dy = 0 if best[1] == y else (1 if best[1] > y else -1)
    if dx == 0 and dy == 0:
        return
    shade = tuple(int(v * 0.94) for v in base)
    if dx > 0:      # 光在右：压暗左半
        points = [(px, py), (px, py + ch - 1),
                  (px + cw // 2, py + ch - 1), (px + cw // 2, py)]
    elif dx < 0:    # 光在左：压暗右半
        points = [(px + cw // 2, py), (px + cw // 2, py + ch - 1),
                  (px + cw - 1, py + ch - 1), (px + cw - 1, py)]
    elif dy > 0:    # 光在下：压暗上半
        points = [(px, py), (px + cw - 1, py),
                  (px + cw - 1, py + ch // 2), (px, py + ch // 2)]
    else:           # 光在上：压暗下半
        points = [(px, py + ch // 2), (px + cw - 1, py + ch // 2),
                  (px + cw - 1, py + ch - 1), (px, py + ch - 1)]
    draw.polygon(points, fill=shade)


def _special_floor(cell: SceneCell) -> bool:
    return bool(cell.terrain and not cell.terrain.solid
                and cell.terrain.aggregate_variant not in ORDINARY_GROUNDS)


def _tier(amount: int, upper: bool) -> int:
    from .glyphs import gas_depth_key, liquid_depth_key
    key = (gas_depth_key if upper else liquid_depth_key)(amount)
    return ({'gas.faint':1,'gas.mid':2,'gas.high':3} if upper else
            {'liquid.shallow':1,'liquid.medium':2,'liquid.deep':3})[key]


def _inside(rect, x: int, y: int) -> bool:
    if not rect:
        return False
    rx, ry, rw, rh = rect
    return rx <= x < rx+rw and ry <= y < ry+rh


def _glyph_scale(cell: SceneCell, cw: int, ch: int, continuous: bool, dot: bool) -> float:
    if cell.actors:
        if min(cw, ch) < SMALL_CELL or (cell.gas and cell.liquid):
            return .72
        return .82
    if cell.items or cell.events:
        return .74
    if cell.terrain and cell.terrain.solid and not continuous:
        return .74
    if cell.terrain and not dot and _special_floor(cell):
        return .74
    return .82


def _draw_texture_band(draw, px, py, cw, ch, color, tier, *, upper, corner):
    band = max(1, round(ch * .3))
    y0 = py if upper else py + ch - band
    for dy in range(band):
        gy = y0 + dy
        for dx in range(cw):
            gx = px + dx
            if _inside(corner, gx, gy):
                continue
            if (dx + dy*2) % 4 < tier:
                draw.point((gx, gy), fill=color)


def _draw_materials(draw, cell: SceneCell, px, py, cw, ch, corner):
    from ..materials import gas_def, liquid_def
    materials = []
    if cell.gas:
        materials.append((True, _hex(gas_def(cell.gas[0]).color), _tier(cell.gas[1], True), cell.gas[1]))
    if cell.liquid:
        materials.append((False, _hex(liquid_def(cell.liquid[0]).color), _tier(cell.liquid[1], False), cell.liquid[1]))
    if not materials:
        return
    small = min(cw, ch) < SMALL_CELL
    if cell.terrain and cell.terrain.solid:
        # 墙体作为前景实体；材料只作为左右边缘纹理，不整宽覆盖上下带。
        edge = max(1, min(3, cw // 8))
        for upper, color, tier, _amount in materials:
            columns = range(edge) if upper else range(cw-edge, cw)
            for dy in range(ch):
                for dx in columns:
                    if (dx + dy*2) % 4 < tier:
                        draw.point((px+dx, py+dy), fill=color)
        return
    if small and len(materials) > 1:
        # 小格：只保留主材料条，另一材料降为角点提示，避免主体被两层带吃掉。
        dominant = max(materials, key=lambda item: item[3])
        upper, color, tier, _amount = dominant
        band = max(1, min(2, ch // 4))
        y0 = py if upper else py + ch - band
        for dy in range(band):
            for dx in range(cw):
                gx, gy = px+dx, y0+dy
                if not _inside(corner, gx, gy):
                    draw.point((gx, gy), fill=color)
        for other_upper, other_color, _other_tier, _amount in materials:
            if other_color == color:
                continue
            mx = px + cw - 2
            my = py + 1 if other_upper else py + ch - 3
            draw.rectangle((mx, my, mx+1, my+1), fill=other_color)
        return
    for upper, color, tier, _amount in materials:
        _draw_texture_band(draw, px, py, cw, ch, color, tier, upper=upper, corner=corner)


def _is_container_cell(cell: SceneCell) -> bool:
    """地面容器（记忆/思绪容器）：占实心格但内容物封存在格内，需要单独画。"""
    terrain = cell.terrain
    return bool(terrain is not None and terrain.solid
                and terrain.wall_kind in CONTAINER_KINDS)


def _draw_container_materials(draw, cell: SceneCell, px, py, cw, ch) -> None:
    """容器内容物：上带气体、下带液体，整宽可辨，且先画材料后画图标。

    地面容器只有 1 格高；旧实现把它当墙体，只画左右 3px 边缘纹理，容器内容
    几乎不可辨（2026-10-22 用户反馈「图像地图分层渲染缺失」）。容器格改为
    上下整宽带：气体在上、液体在下，调用方随后再画容器图标——图标永远压在
    材料带上层，不会被遮住。非容器 solid 仍走 _draw_materials 的边缘纹理。
    """
    from ..materials import gas_def, liquid_def
    materials = []
    if cell.gas:
        materials.append((True, _hex(gas_def(cell.gas[0]).color),
                          _tier(cell.gas[1], True)))
    if cell.liquid:
        materials.append((False, _hex(liquid_def(cell.liquid[0]).color),
                          _tier(cell.liquid[1], False)))
    for upper, color, tier in materials:
        _draw_texture_band(draw, px, py, cw, ch, color, tier,
                           upper=upper, corner=None)


def _draw_stack_badge(draw, cell: SceneCell, px: int, py: int, cw: int, ch: int) -> None:
    count = len(cell.items) + len(cell.events) + len(cell.actors)
    if count <= 1:
        return
    if len(cell.items) > 1:
        color = (225, 195, 110)
    elif len(cell.events) > 1:
        color = (110, 210, 235)
    else:
        color = (230, 120, 120)
    badge = min(3, count - 1)
    w = max(1, min(3, cw // 10))
    step = w + 1
    x = px + cw - w - 1
    y = py + ch - w - 2
    for index in range(badge):
        draw.rectangle((x-index*step, y, x-index*step+w-1, y+w-1), fill=color)


def _draw_elevation_cell(scene, cell, x, y, draw, image, px, py, cw, ch, visual):
    """地势视图的图像画法：固定色阶填底、等高边界画线，轮廓与标记仍可定位。"""
    from ..symbols import symbol
    from .elevation import CONTOUR_COLOR, elevation_bucket, known_elevation
    from .map_presentation import draw_glyph
    tier = known_elevation(cell)
    if cell.terrain is not None and cell.terrain.solid:
        base = _blend(UNKNOWN, _floor_color(cell, scene.realm_id), .62)
    elif tier is None:
        base = _blend(UNKNOWN, _floor_color(cell, scene.realm_id), .18)
    else:
        base = _blend(UNKNOWN, _hex(elevation_bucket(tier)[1]), .82)
    if cell.status == 'memory':
        base = tuple(int(value * MEMORY_DIM) for value in base)
    draw.rectangle((px, py, px + cw - 1, py + ch - 1), fill=base)
    border = _hex(CONTOUR_COLOR, (43, 39, 64))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        other = known_elevation(scene.cell(x + dx, y + dy))
        if other is None or other == tier:
            continue
        if dx:
            edge = (px + (cw - 1 if dx > 0 else 0), py,
                    px + (cw - 1 if dx > 0 else 0), py + ch - 1)
        else:
            edge = (px, py + (ch - 1 if dy > 0 else 0),
                    px + cw - 1, py + (ch - 1 if dy > 0 else 0))
        draw.line(edge, fill=border, width=1)
    if visual and visual.text:
        draw_glyph(image, visual.text, visual.color, (px, py, cw, ch), scale=.78)
    elif cell.actors:
        draw_glyph(image, visual.text if visual else symbol('player', 'themed').strip(),
                   visual.color if visual else '#e8e2d0',
                   (px, py, cw, ch), scale=.78)
    if cell.events:
        draw.rectangle((px + 1, py + 1, px + min(3, max(2, cw // 8)), py + 3),
                       fill=(110, 210, 235))
    if cell.site:
        draw.rectangle((px + cw - 3, py + 1, px + cw - 2, py + 3), fill=(225, 195, 110))
    if cell.danger:
        draw.line((px, py + ch - 1, px + cw - 1, py + ch - 1), fill=(230, 80, 80), width=1)


def _render_scene_image(scene: SceneSnapshot, *, cell_px: tuple[int, int] = (24, 24),
                       show_grid: bool = False, lights=(), backgrounds=None, effect_glyphs=None,
                       fog_backgrounds=None) -> Image.Image:
    """Original-colour material textures around actual, uniformly scaled glyphs.

    ``fog_backgrounds`` 是允许压过迷雾的显式线索底色（声音波次）：与
    ``backgrounds`` 不同，它**不要求**格子处于当前视野——声波本来就只标记
    视野外听到的格。其余叠加层仍走 ``backgrounds`` 的可见性门槛。
    """
    from .map_presentation import draw_glyph, terrain_glyph
    cw, ch = max(2, int(cell_px[0])), max(2, int(cell_px[1]))
    left, top, width, height = scene.viewport
    image = Image.new('RGB', (width*cw, height*ch), UNKNOWN)
    draw = ImageDraw.Draw(image)
    from ..symbols import CONTINUOUS_WALL_KEYS, map_symbol, symbol
    from ..materials import wall_def
    for (x, y), cell in scene.cells.items():
        px, py = (x-left)*cw, (y-top)*ch
        visual = scene.visuals.get((x, y))
        fog = (fog_backgrounds or {}).get((x, y))
        if cell.status == 'unknown':
            if fog:
                draw.rectangle((px, py, px+cw-1, py+ch-1), fill=_hex(fog, UNKNOWN))
            if visual and visual.text and (cell.actors or visual.priority):
                draw_glyph(image, visual.text, visual.color, (px, py, cw, ch),
                           scale=_glyph_scale(cell,cw,ch,False,False))
            continue
        if scene.observe_layer == 'elevation':
            # 邻格档位参与画等高边界，因此这一层不走按格缓存。
            _draw_elevation_cell(scene, cell, x, y, draw, image, px, py, cw, ch, visual)
            from .observation_marks import draw_marks
            if show_grid:
                draw.rectangle((px,py,px+cw-1,py+ch-1),outline=(20,20,26))
            draw_marks(draw, cell, (px,py,cw,ch))
            continue
        if scene.observe_layer in ('floor', 'low', 'middle', 'high'):
            from .map_presentation import spatial_glyph
            base = _blend(UNKNOWN, _floor_color(cell, scene.realm_id), .28)
            if fog:
                base = _hex(fog, base)
            draw.rectangle((px,py,px+cw-1,py+ch-1), fill=base)
            glyph = spatial_glyph(cell)
            color = _hex(glyph.color)
            if cell.status == 'memory':
                color = tuple(int(v*MEMORY_DIM) for v in color)
            if glyph.text:
                if glyph.text in (symbol('floor','themed').strip(), map_symbol('floor','themed').strip()):
                    # Ink-cropping a dot then fitting it to .82 of a tile makes
                    # a giant disk. Keep the same centred floor point instead.
                    radius = max(0, min(cw,ch)//16)
                    cx, cy = px+cw//2, py+ch//2
                    draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius), fill=color)
                else:
                    draw_glyph(image, glyph.text, '#%02x%02x%02x' % color,
                               (px,py,cw,ch), scale=.82)
            _draw_stack_badge(draw, cell, px, py, cw, ch)
            from .observation_marks import draw_marks
            if show_grid:
                draw.rectangle((px,py,px+cw-1,py+ch-1),outline=(20,20,26))
            draw_marks(draw, cell, (px,py,cw,ch))
            continue
        raw_base = _floor_color(cell, scene.realm_id)
        base = _blend(UNKNOWN, raw_base, .28)
        if cell.status in ('visible', 'developed') and lights:
            base = _light_tint(base, lights, x, y, left, top, cw, ch)
        if visual and visual.background and not (cell.liquid or cell.gas):
            base = _hex(visual.background, base)
        if cell.telegraph and visual and visual.background:
            base = _hex(visual.background, base)
        if (backgrounds and cell.status in ('visible','developed') and (x,y) in backgrounds
                and not (cell.terrain and cell.terrain.solid)):
            base = _hex(backgrounds[(x,y)], base)
        if cell.status == 'memory':
            base = tuple(int(v*MEMORY_DIM) for v in base)
        if fog:
            base = _hex(fog, base)
        draw.rectangle((px, py, px+cw-1, py+ch-1), fill=base)
        if (lights and cell.status in ('visible', 'developed')
                and cell.terrain and not cell.terrain.solid
                and not cell.liquid and not cell.gas and not cell.flame
                and not _special_floor(cell)):
            _cell_gradient(draw, base, lights, x, y, px, py, cw, ch)
        terrain = terrain_glyph(cell)
        container_cell = _is_container_cell(cell)
        if container_cell:
            # 容器材料带先画，容器图标在下面统一绘制，保证图标压在最上层。
            _draw_container_materials(draw, cell, px, py, cw, ch)
        # Only the genuinely featureless block is a rectangle. Patterned solid
        # pairs (hardened/dense) retain their own ink, gaps and silhouette.
        continuous = bool(cell.terrain and cell.terrain.solid and
                          wall_def(cell.terrain.wall_kind).symbol_key in ('solid', 'wall.compacted'))
        if continuous:
            wall_color = _hex(terrain.color)
            if cell.status not in ('visible','developed'):
                wall_color = tuple(int(v*.42) for v in wall_color)
            elif lights:
                # §12 C：普通墙受光——整格原色填充不再盖掉底层光色，
                # 改用低比例混合，墙种识别色仍占主体。
                wall_color = _light_tint(wall_color, lights, x, y, left, top,
                                         cw, ch, alpha_scale=.55)
            if fog:
                wall_color = _hex(fog, wall_color)
            # Keep the actual floor background visible around the solid's ink.
            # Even tiny cells must keep ordered, nonnegative rectangle bounds.
            inset=max(1,round(min(cw,ch)*.05))
            x0,y0=px+min(inset,cw-1),py+min(inset,ch-1)
            draw.rectangle((x0,y0,max(x0,px+cw-1-inset),max(y0,py+ch-1-inset)),
                           fill=wall_color)
        dot = terrain.text in (map_symbol('floor','themed').strip(), symbol('floor','themed').strip())
        special = _special_floor(cell)
        corner = None
        if cell.actors and special:
            mark_w = max(2, min(4, cw // 6))
            mark_h = max(2, min(4, ch // 6))
            corner = (px + 1, py + ch - mark_h - 1, mark_w, mark_h)
        if continuous:
            pass
        elif cell.terrain and not cell.terrain.solid and dot:
            color = _hex(terrain.color)
            if cell.status == 'memory':
                color = tuple(int(v*.42) for v in color)
            radius=max(0,round(min(cw,ch)*.045))
            draw.rectangle((px+cw//2-radius,py+ch//2-radius,
                            px+cw//2+radius,py+ch//2+radius),fill=color)
        elif not corner:
            draw_glyph(image, terrain.text, terrain.color, (px, py, cw, ch),
                       scale=_glyph_scale(cell,cw,ch,continuous,dot))
        if not container_cell:
            _draw_materials(draw, cell, px, py, cw, ch, corner)
        if visual:
            if continuous and not (cell.actors or cell.items or cell.events or visual.priority):
                show = False
            elif dot and visual.text == terrain.text:
                show = False
            elif cell.liquid or cell.gas:
                show = bool(cell.actors or cell.items or cell.events or cell.flame or visual.priority)
                show = show or visual.text == symbol('player','themed').strip()
            else:
                show = True
            if show:
                draw_glyph(image, visual.text, visual.color, (px, py, cw, ch),
                           scale=_glyph_scale(cell,cw,ch,continuous,dot))
        elif cell.actors:
            draw_glyph(image, symbol('manifestation','themed'), '#e67878', (px, py, cw, ch), scale=.82)
        if corner:
            # 特殊地板被主体覆盖时保留固定左下角标；角标本身仍是该地板的字形，
            # 不是统一的色点（极小格退化为高对比色块）。
            mark = _hex(terrain.color)
            draw.rectangle((corner[0], corner[1], corner[0]+corner[2]-1, corner[1]+corner[3]-1),
                           fill=_blend(base, mark, .22))
            if corner[2] >= 3 and corner[3] >= 3:
                draw_glyph(image, terrain.text, terrain.color, corner, scale=.88)
            else:
                draw.rectangle((corner[0], corner[1], corner[0]+corner[2]-1, corner[1]+corner[3]-1),
                               fill=mark)
        if cell.events or (visual and visual.priority):
            # 任务/预警先于主体保留：左上固定角标，永不与左下特殊地板角标抢占。
            draw.rectangle((px+1,py+1,px+min(3,max(2,cw//8)),py+3),fill=(110,210,235))
        if cell.site:
            draw.rectangle((px+cw-3,py+1,px+cw-2,py+3),fill=(225,195,110))
        _draw_stack_badge(draw, cell, px, py, cw, ch)
        if cell.danger:
            draw.line((px,py+ch-1,px+cw-1,py+ch-1),fill=(230,80,80),width=1)
        if effect_glyphs and (x,y) in effect_glyphs and cell.status in ('visible','developed'):
            glyph, color = effect_glyphs[(x,y)]
            draw_glyph(image,glyph,color,(px,py,cw,ch),
                       scale=getattr(glyph,'raster_scale',.74))
        if show_grid:
            draw.rectangle((px,py,px+cw-1,py+ch-1),outline=(20,20,26))
        if scene.observe_layer:
            from .observation_marks import draw_marks
            draw_marks(draw, cell, (px,py,cw,ch))
    return image


from functools import lru_cache
from dataclasses import replace

from ..env_compat import get as env_get, name as env_name

IMAGE_PAN_REUSE_ENV = env_name('IMAGE_PAN_REUSE')


def _image_pan_reuse_enabled() -> bool:
    """C5 平移增量开关：每次 render 现读环境变量（默认开启；=0 走旧整张重建）。"""
    return env_get('IMAGE_PAN_REUSE', '1') != '0'


@lru_cache(maxsize=4096)
def _tile(cell, visual, realm, cell_px, show_grid, background, fog_background, effect, observe_layer='', effect_scale=None):
    # effect_scale distinguishes an animation mark from the same plain character
    # in this LRU key; only marked projectile glyphs use a calibrated ink size.
    cell = replace(cell,x=0,y=0)
    snapshot = SceneSnapshot(1,'',realm,(),(0,0,1,1),2,1,{(0,0):cell},
                             {(0,0):visual} if visual else {}, observe_layer=observe_layer)
    return _render_scene_image(snapshot,cell_px=cell_px,show_grid=show_grid,
                               backgrounds={(0,0):background} if background else None,
                               effect_glyphs={(0,0):effect} if effect else None,
                               fog_backgrounds={(0,0):fog_background} if fog_background else None)


def _cell_token(cell, visual, background, fog_background, effect):
    """按格内容键：不含 viewport，所以平移后绝对坐标的旧 token 仍可比较。"""
    return (cell, visual, background, fog_background, effect,
            getattr(effect[0], 'raster_scale', None) if effect else None)


def _paste_cell(image, pos, cell, visual, realm_id, cell_px, show_grid, token,
                observe_layer, left, top):
    tile = _tile(replace(cell, x=0, y=0), visual, realm_id, cell_px, show_grid,
                 token[2], token[3], token[4], observe_layer, token[5])
    image.paste(tile, ((pos[0]-left)*cell_px[0], (pos[1]-top)*cell_px[1]))


class _PanFallback(Exception):
    """平移增量遇到不安全情况：丢弃局部结果，回退整张重建。"""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class SceneImageCache:
    """One viewport raster; update only cells whose permitted facts changed.

    C5 平移增量（docs/261022-卡顿性能进一步优化方案.md 4.2 节）：
    - 缓存键拆成几何键 (cell_px, show_grid, realm_id, observe_layer) 与 viewport；
      几何键变化才整张重建。
    - self.cells 是「绝对坐标 -> token」表，平移时不清空。
    - 视口平移时以旧 image 为底，把新旧视口重叠区 crop+paste 到新图，只重画
      「新视口内、重叠区外」的格子与「重叠区内 token 变化」的格子。
    - 旧图为空 / 视口尺寸变化 / 无重叠（跳变超过一屏）/ 场景非稠密 / 开关关闭 /
      任何异常一律回退整张重建，与整张重建逐像素一致。
    ONEIRSCRIPT_IMAGE_PAN_REUSE=0 关闭平移增量（平移帧仍整张重建）。
    """

    def __init__(self):
        self.geometry = None
        self.viewport = None
        self.cells: dict[tuple[int, int], tuple] = {}
        self.image = None
        self._dense = False
        # 诊断计数（测试/性能报告用，不参与渲染决策）。
        self.full_rebuilds = 0
        self.pan_reuses = 0
        self.painted_cells = 0
        self.last_rebuild_reason = ''

    # -- 整张重建（与旧实现逐像素一致） --------------------------------
    def _rebuild(self, scene, geometry, viewport, backgrounds, effect_glyphs, reason,
                 fog_backgrounds=None):
        cell_px, show_grid = geometry[0], geometry[1]
        cw, ch = cell_px
        left, top, width, height = viewport
        image = Image.new('RGB', (width*cw, height*ch), UNKNOWN)
        tokens = {}
        backgrounds = backgrounds or {}
        effect_glyphs = effect_glyphs or {}
        fog_backgrounds = fog_backgrounds or {}
        inside = True
        for pos, cell in scene.cells.items():
            x, y = pos
            if not (left <= x < left+width and top <= y < top+height):
                inside = False
            visual = scene.visuals.get(pos)
            effect = effect_glyphs.get(pos)
            token = _cell_token(cell, visual, backgrounds.get(pos),
                                fog_backgrounds.get(pos), effect)
            tokens[pos] = token
            _paste_cell(image, pos, cell, visual, scene.realm_id, cell_px,
                        show_grid, token, scene.observe_layer, left, top)
        self.geometry = geometry
        self.viewport = viewport
        self.cells = tokens
        self.image = image
        self._dense = inside and len(tokens) == width*height
        self.full_rebuilds += 1
        self.painted_cells += len(tokens)
        self.last_rebuild_reason = reason

    # -- 平移增量 -----------------------------------------------------
    def _pan_blocker(self, scene, geometry, viewport) -> str:
        """不能走平移增量的原因；空串表示可以。"""
        if self.geometry != geometry:
            return 'geometry'
        if self.image is None or self.viewport is None:
            return 'no-image'
        if not _image_pan_reuse_enabled():
            return 'disabled'
        old_left, old_top, old_w, old_h = self.viewport
        left, top, width, height = viewport
        cw, ch = geometry[0]
        if (old_w, old_h) != (width, height) or self.image.size != (old_w*cw, old_h*ch):
            return 'resize'
        if abs(left-old_left) >= width or abs(top-old_top) >= height:
            # 两屏没有一格重叠：crop+paste 无从复用，等价于整张重建。
            return 'jump'
        if not self._dense or len(scene.cells) != width*height:
            # 只有「上一帧与新帧都铺满视口」时，重叠区像素才可整块信任；
            # 稀疏手动快照走整张重建，与无缓存渲染路径完全一致。
            return 'sparse'
        return ''

    def _pan(self, scene, viewport, backgrounds, effect_glyphs, fog_backgrounds=None):
        cell_px, show_grid = self.geometry[0], self.geometry[1]
        cw, ch = cell_px
        left, top, width, height = viewport
        old_left, old_top, old_w, old_h = self.viewport
        cov_left, cov_right = max(old_left, left), min(old_left+old_w, left+width)
        cov_top, cov_bottom = max(old_top, top), min(old_top+old_h, top+height)
        if cov_right <= cov_left or cov_bottom <= cov_top:
            raise _PanFallback('jump')
        image = Image.new('RGB', (width*cw, height*ch), UNKNOWN)
        image.paste(
            self.image.crop(((cov_left-old_left)*cw, (cov_top-old_top)*ch,
                             (cov_right-old_left)*cw, (cov_bottom-old_top)*ch)),
            ((cov_left-left)*cw, (cov_top-top)*ch))
        tokens = dict(self.cells)
        backgrounds = backgrounds or {}
        effect_glyphs = effect_glyphs or {}
        fog_backgrounds = fog_backgrounds or {}
        painted = 0
        for pos, cell in scene.cells.items():
            x, y = pos
            if not (left <= x < left+width and top <= y < top+height):
                raise _PanFallback('sparse')
            visual = scene.visuals.get(pos)
            effect = effect_glyphs.get(pos)
            token = _cell_token(cell, visual, backgrounds.get(pos),
                                fog_backgrounds.get(pos), effect)
            if (cov_left <= x < cov_right and cov_top <= y < cov_bottom
                    and tokens.get(pos) == token):
                continue
            tokens[pos] = token
            _paste_cell(image, pos, cell, visual, scene.realm_id, cell_px,
                        show_grid, token, scene.observe_layer, left, top)
            painted += 1
        # 原子提交：上面的异常只会丢弃局部图，不会污染缓存状态。
        self.image = image
        self.viewport = viewport
        self.cells = tokens
        self._dense = True
        self.painted_cells += painted

    def _update(self, scene, viewport, backgrounds, effect_glyphs, fog_backgrounds=None):
        cell_px, show_grid = self.geometry[0], self.geometry[1]
        left, top, width, height = viewport
        backgrounds = backgrounds or {}
        effect_glyphs = effect_glyphs or {}
        fog_backgrounds = fog_backgrounds or {}
        image = self.image
        inside = True
        painted = 0
        for pos, cell in scene.cells.items():
            x, y = pos
            if not (left <= x < left+width and top <= y < top+height):
                inside = False
            visual = scene.visuals.get(pos)
            effect = effect_glyphs.get(pos)
            token = _cell_token(cell, visual, backgrounds.get(pos),
                                fog_backgrounds.get(pos), effect)
            if self.cells.get(pos) == token:
                continue
            self.cells[pos] = token
            _paste_cell(image, pos, cell, visual, scene.realm_id, cell_px,
                        show_grid, token, scene.observe_layer, left, top)
            painted += 1
        self._dense = inside and len(scene.cells) == width*height
        self.painted_cells += painted

    def render(self, scene, cell_px, show_grid, backgrounds, effect_glyphs, fog_backgrounds=None):
        cell_px = (int(cell_px[0]), int(cell_px[1]))
        viewport = tuple(int(value) for value in scene.viewport)
        geometry = (cell_px, bool(show_grid), scene.realm_id, scene.observe_layer)
        if self.geometry != geometry:
            self._rebuild(scene, geometry, viewport, backgrounds, effect_glyphs,
                          'first' if self.geometry is None else 'geometry',
                          fog_backgrounds)
            return self.image
        if self.image is None or self.viewport is None:
            self._rebuild(scene, geometry, viewport, backgrounds, effect_glyphs, 'no-image',
                          fog_backgrounds)
            return self.image
        if viewport == self.viewport:
            width, height = viewport[2], viewport[3]
            if self._dense and len(scene.cells) != width*height:
                # 稠密帧突然缺格：旧实现会留残影；整张重建保证与无缓存渲染一致。
                self._rebuild(scene, geometry, viewport, backgrounds, effect_glyphs, 'sparse',
                              fog_backgrounds)
                return self.image
            self._update(scene, viewport, backgrounds, effect_glyphs, fog_backgrounds)
            return self.image
        blocker = self._pan_blocker(scene, geometry, viewport)
        if not blocker:
            try:
                self._pan(scene, viewport, backgrounds, effect_glyphs, fog_backgrounds)
                self.pan_reuses += 1
                return self.image
            except _PanFallback as fallback:
                blocker = fallback.reason
            except Exception:
                # 残影/错位风险高于性能收益：任何异常都整张重建。
                blocker = 'error'
        self._rebuild(scene, geometry, viewport, backgrounds, effect_glyphs,
                      blocker or 'fallback', fog_backgrounds)
        return self.image


def render_scene_image(scene: SceneSnapshot, *, cell_px=(24,24), show_grid=False,
                       lights=(), backgrounds=None, effect_glyphs=None,
                       fog_backgrounds=None, cache=None):
    """Reuse unchanged cell rasters across actions and decorative frames."""
    if lights or scene.observe_layer in ('elevation', 'floor', 'low', 'middle', 'high'):
        # 光照与等高边界都看邻格，按格缓存不适用。
        return _render_scene_image(scene,cell_px=cell_px,show_grid=show_grid,lights=lights,
                                    backgrounds=backgrounds,effect_glyphs=effect_glyphs,
                                    fog_backgrounds=fog_backgrounds)
    cw,ch = max(2,int(cell_px[0])),max(2,int(cell_px[1]))
    if cache is not None:
        return cache.render(scene,(cw,ch),show_grid,backgrounds,effect_glyphs,
                            fog_backgrounds)
    left,top,width,height = scene.viewport
    image = Image.new('RGB',(width*cw,height*ch),UNKNOWN)
    fog_backgrounds = fog_backgrounds or {}
    for pos,cell in scene.cells.items():
        if (cell.status == 'unknown' and not cell.actors
                and not getattr(scene.visuals.get(pos),'priority',False)
                and pos not in fog_backgrounds):
            continue
        effect=(effect_glyphs or {}).get(pos)
        tile = _tile(replace(cell,x=0,y=0),scene.visuals.get(pos),scene.realm_id,(cw,ch),
                     show_grid,(backgrounds or {}).get(pos),fog_backgrounds.get(pos),effect,
                     scene.observe_layer,
                     getattr(effect[0],'raster_scale',None) if effect else None)
        image.paste(tile,((pos[0]-left)*cw,(pos[1]-top)*ch))
    return image
