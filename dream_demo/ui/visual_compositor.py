"""多字符视觉层合成器（2026-10-26，ASCII 动画扩展 Task 2/3）。

把 VisualFrame 里的世界坐标字符层，按设计 §5.4 的顺序投影到像素层：

    terrain → 背景色块 → 背景/余迹字符（低亮） → subjects
    → 前景特效字符（protected_mask 腐蚀挖空） → markers

以及字符后端的格内多字符降级（flatten_visual_text）、覆盖包围盒
（visual_bounds）与前后帧脏区（visual_dirty_cells）。

约定：
- frame 的键、protected/visible 都是世界格坐标；本模块是唯一做视口投影的地方。
- 只读 frame 与 SceneVisualLayers；绘制复用 map_presentation.draw_glyph。
- 只有 UI 层 import 本模块；核心事件合同不依赖 PIL。
- 稳定顺序恒为 frame.sorted_layers()（(z, event_id, 层内序号)），与 dict 插入顺序无关。
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from PIL import Image, ImageColor, ImageDraw, ImageFilter

from .visual_frame import TextGlyph, VisualFrame

# 背景/余迹字符统一压低亮度与不透明度，保证主体与前景主冲击可读（§5.4）。
_AMBIENT_ALPHA = 0.55
_AMBIENT_DIM = 0.65
# ASCII equivalents for the vetted, one-cell animation accents.  Used only
# when the active terminal encoding cannot represent Unicode glyphs.
_ASCII_GLYPH_FALLBACKS = {"·": ".", "○": "o", "◇": "*", "◦": ".", "ϟ": "~"}
# 浮点包围盒换算成整格时的容差，避免恰好落在格边界时多算一格。
_EDGE_EPSILON = 1e-9


@dataclass(frozen=True)
class SceneVisualLayers:
    """授权场景拆出的四层栅格（尺寸均为当前视口像素大小）。

    terrain: 地形/既有光照的 RGB；subjects: 角色/物品/事件主体 RGBA；
    markers: 危险/观察/交互角标 RGBA；protected_mask: 主体必须保留像素的 L
    蒙版。subjects/markers/protected_mask 允许为 None，便于分阶段接入与测试。
    """

    terrain: Image.Image
    subjects: Image.Image | None
    markers: Image.Image | None
    protected_mask: Image.Image | None

    def __post_init__(self):
        if self.terrain is None:
            raise ValueError("SceneVisualLayers.terrain 不能为 None")
        present = [layer for layer in
                   (self.terrain, self.subjects, self.markers, self.protected_mask)
                   if layer is not None]
        sizes = {layer.size for layer in present}
        if len(sizes) > 1:
            raise ValueError(f"SceneVisualLayers 四层尺寸必须相同: {sorted(sizes)}")


# ---------------------------------------------------------------------------
# 合成
# ---------------------------------------------------------------------------
def compose_visual_image(scene_layers, frame, *, viewport, cell_px,
                         protected=frozenset(), visible=None):
    """按 §5.4 顺序把 frame 叠到场景分层上，返回新的 RGB 图。

    viewport=(left, top, width, height) 为世界格；cell_px=(cw, ch)。
    protected 是世界格集合；图片端精确避让由 protected_mask 负责，格级
    protected 不删除整格命中反馈（角色格仍允许边缘字符）。
    visible 为 None 表示不额外裁切。
    """
    left, top, width, height = _viewport(viewport)
    cw, ch = _cell_px(cell_px)
    if width <= 0 or height <= 0 or cw <= 0 or ch <= 0:
        raise ValueError(f"非法视口/格尺寸: viewport={viewport!r} cell_px={cell_px!r}")
    size = (width * cw, height * ch)
    terrain = scene_layers.terrain
    if terrain.size != size:
        raise ValueError(
            f"terrain 尺寸 {terrain.size} 与 viewport*cell_px {size} 不一致")
    base = terrain.convert("RGB") if terrain.mode != "RGB" else terrain.copy()
    visible_cells = _visible_set(visible)
    frame = frame if frame is not None else VisualFrame()

    # 1) 背景色块（作用范围/命中底色），仍在 terrain 之上、字符之下。
    for raw_cell in sorted(frame.backgrounds):
        cell = _cell(raw_cell)
        if _skip_cell(cell, left, top, width, height, visible_cells):
            continue
        _fill_cell(base, cell, frame.backgrounds[raw_cell], left, top, cw, ch)

    # 2) 背景类字符层：role == "ambient" 或 z < 0，低亮画在主体之下。
    for cell, layer in _iter_layers(frame):
        if layer.alpha <= 0 or not _is_background_layer(layer):
            continue
        if _skip_cell(cell, left, top, width, height, visible_cells):
            continue
        _draw_layer(base, layer, cell, left=left, top=top, cell_px=(cw, ch),
                    alpha_scale=_AMBIENT_ALPHA, dim=_AMBIENT_DIM)

    # 3) 原主体（角色/物品/主体），保持在背景余迹之上。
    if scene_layers.subjects is not None:
        base = Image.alpha_composite(
            base.convert("RGBA"), scene_layers.subjects.convert("RGBA"),
        ).convert("RGB")

    # 4) 前景字符层：先记下未叠特效的主体像素，画完后按 protected_mask 腐蚀
    #    1px 恢复主体内部——等价于在 RGBA 覆盖层上把 alpha 挖空再合成，但避免
    #    draw_glyph 的 paste 在透明层上把 alpha 平方一次导致字形边缘变薄。
    foreground = [
        (cell, layer) for cell, layer in _iter_layers(frame)
        if layer.alpha > 0
        and not _is_background_layer(layer)
        and not _skip_cell(cell, left, top, width, height, visible_cells)
    ]
    if foreground:
        protected_pixels = base.copy()
        for cell, layer in foreground:
            _draw_layer(base, layer, cell, left=left, top=top, cell_px=(cw, ch))
        carve = _carve_mask(scene_layers.protected_mask)
        if carve is not None:
            base.paste(protected_pixels, (0, 0), carve)

    # 5) markers 永远最后：危险/观察/交互信息不被任何特效改变。
    if scene_layers.markers is not None:
        base = Image.alpha_composite(
            base.convert("RGBA"), scene_layers.markers.convert("RGBA"),
        ).convert("RGB")
    return base


# ---------------------------------------------------------------------------
# 增量合成：只重画脏格 ±1 邻格（字形 offset/scale 可能跨格）
# ---------------------------------------------------------------------------
def compose_visual_image_incremental(previous, scene_layers, frame, *,
                                     viewport, cell_px, dirty,
                                     protected=frozenset(), visible=None):
    """在上一帧上只重合成脏格及邻格，结果必须与整帧合成逐像素一致。"""
    left, top, width, height = _viewport(viewport)
    cw, ch = _cell_px(cell_px)
    if previous is None:
        return compose_visual_image(scene_layers, frame, viewport=viewport,
                                    cell_px=cell_px, protected=protected, visible=visible)
    cells = {_cell(cell) for cell in (dirty or ())}
    if not cells:
        return previous.copy()
    xs = [cell[0] for cell in cells]
    ys = [cell[1] for cell in cells]
    x0 = max(left, min(xs) - 1)
    x1 = min(left + width - 1, max(xs) + 1)
    y0 = max(top, min(ys) - 1)
    y1 = min(top + height - 1, max(ys) + 1)
    if x1 < x0 or y1 < y0:
        return previous.copy()  # 脏格完全在视口外
    box_w, box_h = x1 - x0 + 1, y1 - y0 + 1
    px0, py0 = (x0 - left) * cw, (y0 - top) * ch
    px1, py1 = px0 + box_w * cw, py0 + box_h * ch

    def _crop(layer):
        return layer.crop((px0, py0, px1, py1)) if layer is not None else None

    sub_layers = SceneVisualLayers(
        _crop(scene_layers.terrain), _crop(scene_layers.subjects),
        _crop(scene_layers.markers), _crop(scene_layers.protected_mask))
    frame = frame if frame is not None else VisualFrame()
    sub_glyphs = {}
    for raw_cell in sorted(frame.glyph_layers):
        cell = _cell(raw_cell)
        if x0 - 1 <= cell[0] <= x1 + 1 and y0 - 1 <= cell[1] <= y1 + 1:
            sub_glyphs[cell] = frame.glyph_layers[raw_cell]
    sub_backgrounds = {}
    for raw_cell in sorted(frame.backgrounds):
        cell = _cell(raw_cell)
        if x0 <= cell[0] <= x1 and y0 <= cell[1] <= y1:
            sub_backgrounds[cell] = frame.backgrounds[raw_cell]
    in_box = frozenset(cell for cell in protected
                       if x0 - 1 <= cell[0] <= x1 + 1 and y0 - 1 <= cell[1] <= y1 + 1)
    sub = compose_visual_image(sub_layers, VisualFrame(sub_glyphs, sub_backgrounds),
                               viewport=(x0, y0, box_w, box_h), cell_px=(cw, ch),
                               protected=in_box, visible=None)
    out = previous.copy()
    out.paste(sub, (px0, py0))
    return out


def flatten_visual_text(frame, *, viewport, cell_columns, cell_rows,
                        protected=frozenset(), visible=None,
                        unicode_supported=True):
    """字符后端的格内多字符投影（§5.4 纯字符降级）。

    返回 (styles, text)：
    - styles: dict[world_cell, str]，形如 '#f2dca0 on #112233'；
    - text: dict[world_cell, tuple[TextGlyph, ...]]，TextGlyph 的 column/row
      是格内局部位置（0..cell_columns-1 / 0..cell_rows-1）。
    protected 格跳过中心列（只留边缘列）；cell_columns==1 时保留主层降级。
    """
    left, top, width, height = _viewport(viewport)
    columns = int(cell_columns)
    rows = int(cell_rows)
    if columns < 1 or rows < 1:
        raise ValueError(f"格内列/行必须为正: {cell_columns!r}, {cell_rows!r}")
    visible_cells = _visible_set(visible)
    protected_cells = {(int(x), int(y)) for x, y in (protected or ())}
    frame = frame if frame is not None else VisualFrame()

    styles: dict = {}
    text: dict = {}
    cells = set(frame.glyph_layers) | set(frame.backgrounds)
    for raw_cell in sorted(cells):
        cell = _cell(raw_cell)
        if _skip_cell(cell, left, top, width, height, visible_cells):
            continue
        ordered = [layer for _index, layer in frame.ordered_layers(cell)
                   if layer.alpha > 0]
        background = frame.backgrounds.get(raw_cell, "")
        if not ordered and not background:
            continue
        primary = _primary_layer(ordered)
        styles[cell] = _style_text(primary.color if primary is not None else "",
                                   background)
        if not ordered:
            continue
        projected = _project_text_layers(ordered, columns, rows,
                                          unicode_supported=unicode_supported)
        if cell in protected_cells:
            if columns == 1:
                # 单列格没有边缘列可留：保留主层（最高 z）降级。
                text[cell] = (projected[-1],)
            else:
                center = _center_index(columns)
                kept = tuple(glyph for glyph in projected if glyph.column != center)
                if kept:
                    text[cell] = kept
        else:
            text[cell] = projected
    return styles, text


# ---------------------------------------------------------------------------
# 覆盖范围与脏区
# ---------------------------------------------------------------------------
def visual_bounds(frame, *, viewport, cell_px):
    """返回 frame 覆盖的世界格集合（字形按 scale/offset 的包围盒，跨格含邻格）。

    alpha==0 的层与空 frame 不产生覆盖；背景色块覆盖整格本身。
    """
    left, top, _width, _height = _viewport(viewport)
    cw, ch = _cell_px(cell_px)
    frame = frame if frame is not None else VisualFrame()
    covered: set = set()
    for raw_cell in frame.backgrounds:
        covered.add(_cell(raw_cell))
    for raw_cell, layers in frame.glyph_layers.items():
        cell = _cell(raw_cell)
        for layer in layers:
            if layer.alpha <= 0:
                continue
            covered.update(_glyph_cells(cell, layer, left, top, cw, ch))
    return frozenset(covered)


def visual_dirty_cells(previous, current, *, viewport, cell_px):
    """前后帧覆盖并集 + 内容变化格，裁切到视口，供现有脏区补丁链路使用。

    frame 为空时仍返回上一帧覆盖，保证实例删除/alpha 归零能恢复旧尾迹。
    """
    left, top, width, height = _viewport(viewport)
    _cell_px(cell_px)
    previous = previous if previous is not None else VisualFrame()
    current = current if current is not None else VisualFrame()
    dirty: set = set()
    dirty |= set(visual_bounds(previous, viewport=(left, top, width, height),
                               cell_px=cell_px))
    dirty |= set(visual_bounds(current, viewport=(left, top, width, height),
                               cell_px=cell_px))
    for raw_cell in set(previous.glyph_layers) | set(current.glyph_layers):
        cell = _cell(raw_cell)
        if _cell_signature(previous, cell) != _cell_signature(current, cell):
            dirty.add(cell)
    background_cells = set(previous.backgrounds) | set(current.backgrounds)
    for raw_cell in background_cells:
        cell = _cell(raw_cell)
        if previous.backgrounds.get(raw_cell) != current.backgrounds.get(raw_cell):
            dirty.add(cell)
    return frozenset(
        cell for cell in dirty
        if left <= cell[0] < left + width and top <= cell[1] < top + height
    )


# ---------------------------------------------------------------------------
# 内部：投影与绘制
# ---------------------------------------------------------------------------
def _viewport(viewport):
    left, top, width, height = (int(value) for value in viewport)
    return left, top, width, height


def _cell_px(cell_px):
    cw, ch = (int(value) for value in cell_px)
    return cw, ch


def _cell(raw_cell):
    return int(raw_cell[0]), int(raw_cell[1])


def _visible_set(visible):
    if visible is None:
        return None
    return {(int(x), int(y)) for x, y in visible}


def _skip_cell(cell, left, top, width, height, visible_cells):
    if not (left <= cell[0] < left + width and top <= cell[1] < top + height):
        return True
    if visible_cells is not None and cell not in visible_cells:
        return True
    return False


def _iter_layers(frame):
    for cell, layer in frame.sorted_layers():
        yield cell, layer


def _is_background_layer(layer):
    return layer.role == "ambient" or layer.z < 0


def _primary_layer(ordered):
    """主层：最高 z 的非背景类层；没有则取最高 z 的任意层。"""
    foreground = [layer for layer in ordered if not _is_background_layer(layer)]
    if foreground:
        return foreground[-1]
    return ordered[-1] if ordered else None


def _style_text(color, background):
    color = str(color or "")
    background = str(background or "")
    if color and background:
        return f"{color} on {background}"
    if color:
        return color
    if background:
        return f"on {background}"
    return ""


def _project_index(offset, size):
    center = (size - 1) / 2.0
    value = int(math.floor(center + float(offset) * size + 0.5))
    return max(0, min(size - 1, value))


def _center_index(size):
    return int(math.floor((size - 1) / 2.0 + 0.5))


def _project_text_layers(ordered, columns, rows, *, unicode_supported=True):
    projected = []
    for layer in ordered:
        glyph = layer.glyph
        if not unicode_supported:
            glyph = "".join(
                char if ord(char) < 128 else _ASCII_GLYPH_FALLBACKS.get(char, "?")
                for char in glyph
            )
        projected.append(TextGlyph(
            column=_project_index(layer.offset[0], columns),
            row=_project_index(layer.offset[1], rows),
            glyph=glyph,
            style=layer.color,
        ))
    return tuple(projected)


def _draw_layer(image, layer, cell, *, left, top, cell_px,
                alpha_scale=1.0, dim=1.0):
    """把一个 GlyphLayer 画进格内（rect 中心 = 格中心 + offset*cell_px）。"""
    cw, ch = cell_px
    alpha = max(0.0, min(1.0, float(layer.alpha) * float(alpha_scale)))
    if alpha <= 0.0:
        return
    x = (cell[0] - left) * cw + int(round(layer.offset[0] * cw))
    y = (cell[1] - top) * ch + int(round(layer.offset[1] * ch))
    from .map_presentation import draw_glyph
    draw_glyph(image, layer.glyph, _dim_color(layer.color, dim), (x, y, cw, ch),
               scale=layer.scale, alpha=alpha)


def _fill_cell(image, cell, color, left, top, cw, ch):
    px = (cell[0] - left) * cw
    py = (cell[1] - top) * ch
    ImageDraw.Draw(image).rectangle(
        (px, py, px + cw - 1, py + ch - 1), fill=_rgb(color))


def _rgb(color):
    text = str(color or "").strip()
    if not text:
        return (255, 255, 255)
    try:
        rgb = ImageColor.getrgb(text)
    except ValueError:
        value = ""
        try:
            from .map_presentation import foreground
            value = foreground(text)
        except Exception:  # pragma: no cover - 仅异常色名兜底
            value = ""
        if not value:
            return (255, 255, 255)
        rgb = ImageColor.getrgb(value)
    return tuple(int(channel) for channel in rgb[:3])


def _dim_color(color, factor):
    if factor >= 1.0:
        return color
    rgb = _rgb(color)
    return tuple(max(0, min(255, int(channel * factor))) for channel in rgb)


def _carve_mask(protected_mask):
    if protected_mask is None:
        return None
    mask = protected_mask if protected_mask.mode == "L" else protected_mask.convert("L")
    # 腐蚀 1px：只挖掉主体内部，保留边缘/脚下/背后的字符。
    return mask.filter(ImageFilter.MinFilter(3))


def _glyph_cells(cell, layer, left, top, cw, ch):
    center_x = (cell[0] - left) * cw + cw / 2.0 + float(layer.offset[0]) * cw
    center_y = (cell[1] - top) * ch + ch / 2.0 + float(layer.offset[1]) * ch
    half_w = cw * float(layer.scale) / 2.0
    half_h = ch * float(layer.scale) / 2.0
    x0, x1 = center_x - half_w, center_x + half_w
    y0, y1 = center_y - half_h, center_y + half_h
    col0 = int(math.floor(x0 / cw)) + left
    col1 = int(math.ceil(x1 / cw - _EDGE_EPSILON)) - 1 + left
    row0 = int(math.floor(y0 / ch)) + top
    row1 = int(math.ceil(y1 / ch - _EDGE_EPSILON)) - 1 + top
    return [(x, y) for x in range(col0, col1 + 1) for y in range(row0, row1 + 1)]


def _cell_signature(frame, cell):
    layers = tuple(
        (layer.glyph, layer.color, layer.offset, layer.scale, layer.alpha,
         layer.z, layer.role, layer.event_id, layer.clock_mode)
        for _index, layer in frame.ordered_layers(cell)
        if layer.alpha > 0
    )
    return (layers, frame.backgrounds.get(cell, ""))
