"""地图生成（兼容门面）。

实现已按职责拆分到 :mod:`dream_demo.mapgen`：
layout（层型与尺寸）/ forms（各层型掩码生成）/ doors（门位）/ elevation（地势场）。
本模块保留原导入路径，供旧代码与测试使用；新代码请直接导入 ``dream_demo.mapgen``。
"""

from .mapgen import (
    CORRIDOR_ASPECT,
    MAP_FORMS,
    braid_dead_ends,
    generate_elevation,
    generate_solid_mask,
    generate_solid_mask_with_vaults,
    layer_dimensions,
    layer_form_for,
    layer_form_plan,
    normalize_map_form,
    place_doors,
    room_rects,
)

__all__ = [
    "CORRIDOR_ASPECT",
    "MAP_FORMS",
    "braid_dead_ends",
    "generate_elevation",
    "generate_solid_mask",
    "generate_solid_mask_with_vaults",
    "layer_dimensions",
    "layer_form_for",
    "layer_form_plan",
    "normalize_map_form",
    "place_doors",
    "room_rects",
]
