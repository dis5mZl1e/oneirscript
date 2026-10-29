"""Shared glyph presentation and aspect-preserving rasterization.

The compatibility renderer remains the authority for existing icon routes,
disguises, sensed anomalies, circuits and telegraphs. Capture its permission-
filtered foreground once; both outputs consume that presentation snapshot.
"""
from dataclasses import dataclass, replace
from functools import lru_cache
from types import MappingProxyType

from rich.style import Style
from rich.text import Text

from ..symbols import map_symbol, symbol
from ..materials import floor_def, wall_def, liquid_def, gas_def
from .frame_geometry import cell_ranges
from .glyphs import normalize_tile_glyph, compact_tile_glyph, gas_depth_key, liquid_depth_key


@dataclass(frozen=True)
class SceneGlyph:
    text: str
    color: str
    background: str = ""
    priority: bool = False


@lru_cache(maxsize=2048)
def foreground(style):
    if not isinstance(style, Style):
        style = Style.parse(style or '')
    if style.color is None:
        return ''
    return '#{:02x}{:02x}{:02x}'.format(*style.color.get_truecolor())


# 字符高刷模式（2026-10-25，设置 map_character_fast）：默认关闭。字符后端只画
# 文本，不读 SceneSnapshot.visuals（只有图像后端消费逐格视觉事实）；开启后
# 跳过这份逐格反解。需要 visual 的调用方（F2 预览）显式传 ``visuals``，
# 走 M2-A 快路径，不受此开关影响。
_character_fast = False


def set_character_fast(enabled: bool) -> None:
    global _character_fast
    _character_fast = bool(enabled)


def character_fast_enabled() -> bool:
    return _character_fast



def present_scene(scene, frame: Text, *, priority=(), source_cell_w=None, ranges=None,
                  visuals=None):
    """把一帧文本转换成图像后端消费的逐格视觉事实。

    ``visuals`` 是 2026-10-24（M2-A）的快速入口：render_map / render_observation
    在绘制同一帧时就把每格的（字形、样式、底色）记进这个字典，这里只需转成
    SceneGlyph。旧路径（从 Text 反解）保留给字符后端与等价测试做对照。
    键是世界坐标，与 SceneSnapshot.visuals 一致。
    """
    left, top, width, height = scene.viewport
    if visuals is not None:
        glyphs = {}
        for pos, (text, style, background) in visuals.items():
            glyphs[pos] = SceneGlyph(text, foreground(style) or '#aab3bd',
                                     background or '', pos in priority)
        return replace(scene, visuals=MappingProxyType(glyphs))
    if _character_fast:
        return scene
    # ``ranges`` 允许调用方把已经算过的切片表递进来（2026-10-21 任务3）：
    # 同一帧的 cell_ranges 以前在 present_scene 与 map 控件里各算一次。
    if ranges is None:
        ranges = cell_ranges(frame, width, height, source_cell_w or scene.cell_w, scene.cell_h)
    colors = [foreground(frame.style) or '#aab3bd'] * len(frame.plain)
    backgrounds = [''] * len(frame.plain)
    for span in frame.spans:
        style = span.style if isinstance(span.style,Style) else Style.parse(span.style)
        if style.bgcolor:
            bg = '#{:02x}{:02x}{:02x}'.format(*style.bgcolor.get_truecolor())
            backgrounds[span.start:span.end] = [bg] * (span.end-span.start)
        color = foreground(span.style)
        if color:
            colors[span.start:span.end] = [color] * (span.end-span.start)
    glyphs = {}
    for (x, y), rows in ranges.items():
        row = rows[(len(rows)-1)//2] if rows else (0, 0)
        start, end = row
        value = frame.plain[start:end].strip()
        if value:
            index = next((i for i in range(start, end) if not frame.plain[i].isspace()), start)
            glyphs[(x+left, y+top)] = SceneGlyph(value, colors[index],backgrounds[index],(x+left,y+top) in priority)
    return replace(scene, visuals=MappingProxyType(glyphs))


def terrain_glyph(cell, mode='themed', wide=True):
    terrain = cell.terrain
    if terrain is None:
        return SceneGlyph('', '#07070b')
    if cell.plant and cell.status in ('visible','developed'):
        from ..materials import plant_def_for
        definition = plant_def_for(cell.plant)
        key, color = definition.key, definition.color
    elif terrain.solid:
        definition = wall_def(terrain.wall_kind)
        key, color = definition.symbol_key, definition.color
    else:
        definition = floor_def(terrain.aggregate_variant)
        from .styles import AGGREGATE_STYLES
        key = definition.symbol_key
        color = foreground(AGGREGATE_STYLES.get(terrain.aggregate_variant,'grey50')) or '#64717e'
    value = (map_symbol if wide else symbol)(key, mode)
    return SceneGlyph(value.strip(), color)


def elevation_presentation(scene, cell, x, y, mode):
    """地势视图专用画法（docs §15.4）：高低明暗＋等高边界，不靠颜色单点辨识。

    固体与未记录格保留地形轮廓，玩家格保留自身图标，两者都仍可定位；接触边界
    用背景色带出来（图像后端画同样的边界线），未知格仍然只是黑幕。
    """
    from .elevation import CONTOUR_COLOR, elevation_glyph, known_elevation
    tier = known_elevation(cell)
    if cell.terrain is not None and cell.terrain.solid:
        glyph = terrain_glyph(cell, mode, scene.cell_w > 1)
    elif cell.actors:
        glyph = SceneGlyph(symbol('player', mode).strip(), '#e8e2d0')
    elif tier is None:
        return terrain_glyph(cell, mode, scene.cell_w > 1)
    else:
        text, color = elevation_glyph(cell, wide=scene.cell_w > 1)
        glyph = SceneGlyph(text, color)
    if tier is None:
        return glyph
    edges = [cell_elevation for cell_elevation in
             (known_elevation(scene.cell(x + dx, y + dy)) for dx, dy in
              ((1, 0), (-1, 0), (0, 1), (0, -1)))
             if cell_elevation is not None and cell_elevation != tier]
    return replace(glyph, background=CONTOUR_COLOR if edges else glyph.background)


def spatial_glyph(cell, mode='themed', wide=True):
    """One filtered occupancy view, shared by raster and terminal output."""
    actors = [o for o in cell.occupants if o.kind in ('actor','marker')]
    items = [o for o in cell.occupants if o.kind == 'item']
    if actors or items:
        occupant = (actors or items)[0]
        value = occupant.icon
        if occupant.kind == 'item':
            from ..symbols import glyph_for
            value = glyph_for(value, 'manifestation', mode)
        elif len(value) > 1:
            value = (map_symbol if wide else symbol)(value, mode)
        return SceneGlyph(value.strip(), occupant.color)
    if cell.gas:
        return SceneGlyph(symbol(gas_depth_key(cell.gas[1]), mode).strip(),
                          gas_def(cell.gas[0]).color)
    if cell.liquid:
        return SceneGlyph(symbol(liquid_depth_key(cell.liquid[1]), mode).strip(),
                          liquid_def(cell.liquid[0]).color)
    if cell.flame:
        return SceneGlyph(symbol('fire', mode).strip(), '#ff8a3d')
    return terrain_glyph(cell, mode, wide)


def render_observation(scene, layer, mode='themed', markers=None, visuals=None):
    """Only the filtered scene is read: hiding gas never recalculates vision.

    ``markers`` 是观察层允许叠加的显式标记（声音线索，docs §16.7）：只盖
    发声格字形，不改变该格状态、不照亮周围，未知格仍保持黑幕。
    ``visuals`` 给出时同步记录每格（字形、样式、底色），供 present_scene 的
    图像快速路径直接消费，免去从文本反解（M2-A，2026-10-24）。
    """
    from .observation_marks import marks_for
    result = Text()
    left, top, width, height = scene.viewport
    for y in range(top, top+height):
        cells = []
        for x in range(left, left+width):
            cell = scene.cell(x, y)
            glyph = terrain_glyph(cell, mode, scene.cell_w > 1)
            if cell.status == 'unknown' and not cell.actors:
                glyph = SceneGlyph('', '#07070b')
            elif layer in ('floor', 'low', 'middle', 'high', 'composite', 'sound'):
                glyph = spatial_glyph(cell, mode, scene.cell_w > 1)
            elif layer == 'elevation':
                glyph = elevation_presentation(scene, cell, x, y, mode)
            elif layer == 'liquid' and cell.liquid:
                glyph = SceneGlyph(symbol(liquid_depth_key(cell.liquid[1]), mode).strip(),
                                   liquid_def(cell.liquid[0]).color)
            elif layer == 'gas' and cell.gas:
                glyph = SceneGlyph(symbol(gas_depth_key(cell.gas[1]), mode).strip(),
                                   gas_def(cell.gas[0]).color)
            public = next((a for a in cell.actors if a.always_visible), None)
            if public is not None:
                glyph = SceneGlyph(symbol(public.icon_key, mode).strip(), '#e59b9b')
            if cell.status == 'memory':
                rgb = Style.parse(glyph.color).color.get_truecolor()
                glyph = SceneGlyph(glyph.text,
                                   '#{:02x}{:02x}{:02x}'.format(*(int(v*.42) for v in rgb)),
                                   glyph.background)
            if markers and (x, y) in markers:
                glyph = SceneGlyph(str(markers[(x, y)])[:1], '#e1bd74', glyph.background)
            value = (compact_tile_glyph(glyph.text) if scene.cell_w == 1 else
                     normalize_tile_glyph(glyph.text, mode).center(scene.cell_w))
            background = glyph.background or '#07070b'
            if visuals is not None:
                text = value.strip()
                if text:
                    visuals[(x, y)] = (text, f'{glyph.color} on {background}', background)
            cells.append((value, glyph.color, background, bool(marks_for(cell))))
        for row in range(scene.cell_h):
            for value, color, background, marked in cells:
                result.append(value if row == (scene.cell_h-1)//2 else ' '*scene.cell_w,
                              style=f'{color} on {background}'+(' bold underline' if marked else ''))
            if y < top+height-1 or row < scene.cell_h-1:
                result.append('\n')
    return result


def font_sources():
    from ..terminal_launch import bundled_font_path
    path = bundled_font_path()
    if path is None:
        raise OSError('Bundled map font unavailable')
    # 以当前生效字体为键：切换候选后图像端不会继续复用旧字体的缓存。
    return _font_sources(path)


@lru_cache(maxsize=2)
def _font_sources(path):
    from fontTools.ttLib import TTFont
    sources = []
    for font_path in (path, path.parent/'DreamStrataIcons.ttf',
                      path.parent/'DreamStrataMillenniumEmoji.ttf',
                      path.parent/'DreamStrataInterfaceIcons.ttf',
                      path.parent/'DreamStrataMaterialIcons.ttf',
                      path.parent/'DreamStrataDreamIcons.ttf',
                      # 混乱专属异象 👿🖤😇 的单色线框子集（2026-10-27）：
                      # 非彩色字体，glyph_mask 走描边填充。
                      path.parent/'DreamStrataChaosOutline.ttf'):
        if font_path.exists():
            with TTFont(font_path, lazy=True) as face:
                sources.append((str(font_path), frozenset(face.getBestCmap())))
    return tuple(sources)


@lru_cache(maxsize=8)
def raster_font(path, size):
    from PIL import ImageFont
    return ImageFont.truetype(path,size)


@lru_cache(maxsize=2048)
def glyph_source(value):
    sources = font_sources()
    path = next((path for path, codes in sources
                 if all(ord(c) in codes for c in value.strip())), sources[1][0])
    return path, 'MillenniumEmoji' in path


@lru_cache(maxsize=8192)
def glyph_mask(value, width, height, scale=.82):
    """Crop real ink bounds then scale uniformly; never stretch an outline."""
    from PIL import Image, ImageDraw
    value = value.strip()
    if not value:
        return None
    # Continuous wall pairs remain pairs. Duplicating an identical narrow icon
    # purely to fill two terminal columns is unnecessary in the image backend.
    font_path, embedded_color = glyph_source(value)
    try:
        font = raster_font(font_path, 96)
    except OSError:
        # CBDT emoji has fixed-size strikes; retain this exact font's colour ink.
        font = raster_font(font_path, 109)
    box = font.getbbox(value)
    canvas = Image.new('RGBA', (max(1,box[2]-box[0]), max(1,box[3]-box[1])))
    ImageDraw.Draw(canvas).text((-box[0],-box[1]), value, font=font, fill='white',
                               embedded_color=embedded_color)
    box = canvas.getbbox()
    if box is None:
        return None
    canvas = canvas.crop(box)
    scale = float(scale)
    fit = min(max(1,width)*scale/canvas.width, max(1,height)*scale/canvas.height)
    return canvas.resize((max(1,round(canvas.width*fit)), max(1,round(canvas.height*fit))),
                         Image.Resampling.LANCZOS)


# 图像端缺字回退（2026-10-22）：随包字体没有部分 emoji 字形——实测思绪容器
# 的 🛢（U+1F6E2）不在任何随包字体里，glyph_mask 直接返回 None，图像地图上
# 只剩材料边缘纹理、整格没有图标（用户反馈「图像地图不正常显示图标」）。
# 这里给栅格端一份候选表：原字形优先，缺字时按顺序回退到同主题、字体可画的
# 字形；颜色仍由调用方按材料/地形身份色提供，所以回退不会丢失身份。
# ⚠️ 只影响图像栅格：字符端的 symbol() 输出保持 ⚱/🛢 不变。
_RASTER_GLYPH_FALLBACKS: dict[str, tuple[str, ...]] = {
    '🛢': ('▨', '▧', '▤', '▣'),
}


def raster_glyph_options(value: str) -> tuple[str, ...]:
    """图像栅格的字形候选：原字形优先，缺字时按回退表降级。"""
    value = str(value or '').strip()
    if not value:
        return ()
    return (value, *_RASTER_GLYPH_FALLBACKS.get(value, ()))


@lru_cache(maxsize=8192)
def glyph_mask_compatible(value, width, height, scale=.82):
    """glyph_mask 的缺字回退版本，返回 (实际使用的字形, mask)。

    与 glyph_mask 一样缓存；mask 为 None 时才继续尝试候选表，正常字形
    的行为与直接调用 glyph_mask 完全一致。
    """
    for candidate in raster_glyph_options(value):
        mask = glyph_mask(candidate, width, height, scale)
        if mask is not None:
            return candidate, mask
    return str(value or '').strip(), None


def _ink_rgb(color) -> str:
    """把「名字色」与「#hex」统一成 PIL 能吃的真彩色。

    植物表里有 Rich 名字色（如发光地衣的 ``bright_yellow``），文字后端直接用
    名字，图像后端 ``Image.new(..., color)`` 只认真彩色——不归一化就会在
    「图像模式 + 地衣在视野里」时抛 ``unknown color specifier``。
    """
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        return tuple(int(v) for v in color[:3])
    return foreground(color) or '#ffffff'


def draw_glyph(image, value, color, rect, scale=.82, alpha=1.0):
    from PIL import Image
    x, y, width, height = rect
    # 缺字时先按回退表取可画字形（只影响图像端；颜色仍是调用方给的身份色）。
    value, mask = glyph_mask_compatible(value, width, height, scale)
    if mask is None:
        return
    if not glyph_source(value)[1]:
        ink = Image.new('RGBA', mask.size, _ink_rgb(color))
        ink.putalpha(mask.getchannel('A'))
    else:
        ink = mask
    if alpha < 1.0:
        if ink is mask:
            # glyph_mask results are lru_cache'd; never fade a shared cache entry.
            ink = ink.copy()
        ink.putalpha(ink.getchannel('A').point(lambda v: int(v * alpha)))
    image.paste(ink, (x+(width-ink.width)//2, y+(height-ink.height)//2), ink)
