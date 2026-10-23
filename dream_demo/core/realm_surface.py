"""Bounded, validated floor palettes shared by realm snapshots and rendering."""
from __future__ import annotations

import re

HOSPITAL_BG = '#b7b8b8'
FLOOR_COLORS = {
    'library_palace': {'木质聚合物':'#b89e72','书页地':'#dfcea0','吸声聚合物':'#c3b189',
                       '干纸堆':'#dcc596','防火石面':'#bcb5a1'},
    'white_sanatorium': {'密封板':'#a9b0b2','反光聚合物':'#c1c3c3','海绵聚合物':'#b8b4aa',
                         '金属聚合物':'#a7afb3','粗糙聚合物':'#aaadab','绝热层':'#b4b0aa','吸声聚合物':'#aeb0b3'},
}


# §12 C：位面地面的「按材质职责保护」白名单。
# 只保护承担识别职责的材质（纸页/釉板），普通聚合物走廊仍接收彩光——
# 旧实现把整个位面的地面一律锁死，等于新增彩光在这些位面完全看不见。
PROTECTED_FLOOR_VARIANTS = {
    'library_palace': frozenset({'书页地', '干纸堆', '防火石面'}),
    'white_sanatorium': frozenset({'洁白釉板'}),
}


def protects_floor(state, x, y) -> bool:
    """该格地面是否按材质受保护（不吃彩光）。"""
    variants = PROTECTED_FLOOR_VARIANTS.get(getattr(state, 'realm_id', ''), None)
    if not variants:
        return False
    return state.cell(x, y).aggregate_variant in variants


def display_zones(state):
    zones=normalize_bg_zones(state.realm_bg_zones,state.width,state.height)
    if state.realm_id=='white_sanatorium':
        zones=[dict(z,color=HOSPITAL_BG if z['color']=='#dcdcdf' else z['color']) for z in zones]
    if state.realm_id in FLOOR_COLORS:
        base=HOSPITAL_BG if state.realm_id=='white_sanatorium' else '#e8d8a6'
        # The foundation extends beneath structural outer walls and furniture.
        zones=[{'rect':(0,0,state.width-1,state.height-1),'color':base},*zones]
    return zones


def surface_color(state,x,y,zones):
    color=None
    for zone in zones:
        x0,y0,x1,y1=zone['rect']
        if x0<=x<=x1 and y0<=y<=y1:color=zone['color']
    variant=state.cell(x,y).aggregate_variant
    return FLOOR_COLORS.get(state.realm_id,{}).get(variant,color)


def cached_surface_color(state, x, y, zones, cache):
    """渲染调用内复用地面色（docs §11 P1）：zone 列表每格只扫一次。

    缓存必须由单次渲染/快照的调用方显式持有并丢弃，不能挂在 state 上跨调用
    复用——测试/脚本会直接改地板变体而不推进时间，跨调用缓存会读到旧颜色。
    """
    key = (x, y)
    if key not in cache:
        cache[key] = surface_color(state, x, y, zones)
    return cache[key]


def normalize_bg_zones(zones, width: int, height: int) -> list[dict]:
    if not isinstance(zones, (list, tuple)) or width <= 0 or height <= 0:
        return []
    result = []
    for zone in zones[:64]:
        if not isinstance(zone, dict):
            continue
        rect, color = zone.get("rect"), zone.get("color")
        if not isinstance(rect, (list, tuple)) or len(rect) != 4:
            continue
        if any(type(value) is not int for value in rect):
            continue
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            continue
        x0, y0, x1, y1 = rect
        if x0 > x1 or y0 > y1 or x1 < 0 or y1 < 0 or x0 >= width or y0 >= height:
            continue
        result.append({"rect": (max(0, x0), max(0, y0), min(width-1, x1), min(height-1, y1)),
                       "color": color.lower()})
    return result
