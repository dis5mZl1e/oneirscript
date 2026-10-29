"""Subtle glass surfaces for menu controls, composited over the actual backdrop."""
from functools import lru_cache
from rich.cells import get_character_cell_size
from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip

from .deco import mix_hex


@lru_cache(maxsize=16384)
def _glass_colors(base, accent, width, height, x, y, active, disabled):
    # 2026-10-24 对比度批次（玩家反馈主页选项颜色难分辨）：透明合成机制不变，
    # 把 accent 的存在感提上来——底色混入 .055→.085、边缘 .40→.58（选中更强），
    # 每个按钮的色相环+文字色负责区分，玻璃仍是叠在门景上的透明合成。
    strength = .04 if disabled else .18 if active else .085
    center = max(0., 1. - abs(2 * x / max(1, width - 1) - 1))
    sheen = center * .045 + (1 - y / max(1, height - 1)) * .025
    background = mix_hex(base, accent, strength + sheen)
    edge = mix_hex(base, accent, .82 if active else .58)
    if y == 0:
        edge = mix_hex(edge, '#dcecf2', .10 + center * .18)
    return background, edge


@lru_cache(maxsize=8192)
def _glass_style(source, background, edge):
    style = (source or Style()) + Style(bgcolor=background)
    return style + Style(color=edge) if edge is not None else style


@lru_cache(maxsize=512)
def _glass_row(source, length, backgrounds, accent, width, height, start, y, active, disabled):
    segments, x = [], start
    for segment in source:
        if segment.control:
            segments.append(segment)
            continue
        for char in segment.text:
            span = get_character_cell_size(char)
            index = x - start
            base = backgrounds[index] if 0 <= index < len(backgrounds) else '#101018'
            background, edge = _glass_colors(base, accent, width, height, x, y, active, disabled)
            border = char.strip() and (y in (0, height - 1) or x in (0, width - 1))
            segments.append(Segment(char, _glass_style(segment.style, background, edge if border else None)))
            x += span
    return Strip(list(Segment.simplify(segments)), length)


class GlassButtonMixin:
    """Keep native button geometry/input while replacing opaque variant fills."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        name = self.id or ''
        if name.startswith(('home-', 'slot-', 'delete-', 'catalog-category-',
                            'settings-category-')) or name == 'test-mode':
            self.add_class('glass-button')

    def _glass_accent(self):
        name = self.id or ''
        if name.startswith('delete-') or name == 'home-exit':
            return '#d99587'
        if name.startswith('catalog-category-') or name == 'home-catalog':
            return '#d8bf85'
        if name == 'home-history':
            return '#bca5db'
        if name.startswith('settings-category-') or name == 'home-settings':
            return '#94bdd9'
        # 入梦此前与图鉴/设置分类共用默认青，六项里少一个独立色相；改为薄荷绿，
        # 测试模式/存档槽用中性钢青垫底（2026-10-24 主页选项两两可辨批次）。
        if name == 'home-enter':
            return '#8fe6b5'
        if name == 'test-mode' or name.startswith('slot-'):
            return '#a9b6d8'
        return '#9acbc5'

    def render(self):
        if not self.has_class('glass-button'):
            return super().render()
        # Button's implicit label padding wastes the narrow category tab width.
        label = self.label.copy()
        label.no_wrap = True
        label.overflow = 'ellipsis'
        label.stylize_before(self.rich_style)
        return label

    def render_lines(self, crop):
        strips = super().render_lines(crop)
        if not self.has_class('glass-button'):
            return strips
        from .home_scene import HomeScene

        scene = self.app.query_one(HomeScene)
        accent = self._glass_accent()
        active = (self.has_class('selected') or self.has_class('category-candidate')
                  or self.has_focus or self.mouse_hover)
        width, height = self.region.width, self.region.height
        origin_x, origin_y = self.region.offset - scene.region.offset
        scene_height = scene.size.height
        scene_visible = scene.display
        disabled = self.disabled
        for row, strip in enumerate(strips):
            y = crop.y + row
            backgrounds = []
            sy = origin_y + y
            if scene_visible and 0 <= sy < scene_height:
                backgrounds = scene.background_color_row(sy)
            colors = tuple(backgrounds[x] if 0 <= x < len(backgrounds) else '#101018'
                           for x in range(origin_x + crop.x, origin_x + crop.x + strip.cell_length))
            strips[row] = _glass_row(tuple(strip), strip.cell_length, colors, accent,
                                     width, height, crop.x, y, active, disabled)
        return strips
