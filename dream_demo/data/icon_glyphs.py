"""Stable private-use assignments, compatible text, and archived pixel studies.

Only the game's private font configuration may enable these icons. A PUA glyph
occupies one terminal column followed by a reserved space, never a raw wide char.
The font builder uses OFL Noto Emoji/Symbols outlines in the reading grid.
ART retains the original studies for reference; it is not rendered or built.
"""
from ..cell_size import set_cell_size
from ..env_compat import flag as env_flag

FAMILY = 'Dream Strata Icons'
TILE_UNITS = 1180
ART = {
    'heart': ('.##..##.', '########', '########', '.######.', '..####..', '...##...', '........', '........'),
    'door': ('.######.', '.#....#.', '.#.##.#.', '.#.##.#.', '.#..#.#.', '.#....#.', '.######.', '........'),
    'door_open': ('.######.', '.#..###.', '.#..#.#.', '.#..#.#.', '.#..#.#.', '.#..###.', '.######.', '........'),
    'door_lock': ('.######.', '.#....#.', '.#.##.#.', '.#.#..#.', '.#.##.#.', '.#....#.', '.######.', '........'),
    'partition': ('.######.', '.#.#..#.', '.#.#..#.', '.#.#..#.', '.#.#..#.', '.#.#..#.', '.######.', '........'),
    'table': ('........', '.######.', '.######.', '.#....#.', '.#....#.', '.#....#.', '........', '........'),
    'sink': ('....##..', '....#...', '.######.', '.#....#.', '.#.##.#.', '.######.', '..#..#..', '........'),
    'brick': ('.######.', '.#..#.#.', '.######.', '.#.#..#.', '.######.', '.#..#.#.', '.######.', '........'),
    'mesh': ('.######.', '.##.#.#.', '.#.####.', '.##.#.#.', '.#.####.', '.##.#.#.', '.######.', '........'),
    'moon': ('...###..', '..###...', '.###....', '.###....', '.###....', '..###...', '...###..', '........'),
    'plate': ('........', '..####..', '.#....#.', '.#....#.', '..####..', '...##...', '..####..', '........'),
    'electrode': ('.#....#.', '.#.#..#.', '.#.##.#.', '.#..#.#.', '.#.##.#.', '.#..#.#.', '.#....#.', '........'),
    'insulation': ('........', '.######.', '..####..', '........', '..####..', '.######.', '........', '........'),
    'page': ('..###...', '..#.##..', '..#..#..', '..####..', '..#..#..', '..####..', '........', '........'),
    'mushroom': ('...##...', '..####..', '.######.', '.######.', '...##...', '...##...', '..####..', '........'),
    'moon_shroom': ('...##...', '..###...', '.###.##.', '.######.', '...##...', '...##...', '..####..', '........'),
    'hollow_shroom': ('...##...', '..#..#..', '.#....#.', '.######.', '...##...', '...##...', '..####..', '........'),
    'sporebud': ('...#....', '..###...', '.##.##..', '..###...', '...#....', '..###...', '..#.#...', '........'),
    'flower': ('...#....', '..###...', '.##.##..', '..###...', '...#....', '..##.#..', '...##...', '........'),
    'fern': ('..#.....', '..##....', '..#.#...', '.##.....', '..#.##..', '.##.....', '..#.....', '........'),
    'lily': ('..#.....', '..####..', '..#.#...', '..#.##..', '..#.##..', '.##.....', '..#.....', '........'),
    'faceless': ('..####..', '..####..', '..####..', '...##...', '..####..', '.######.', '..#..#..', '..#..#..'),
    'doll': ('...##...', '..####..', '...##...', '.######.', '...##...', '..####..', '..#..#..', '..#..#..'),
    'audience': ('...##...', '..####..', '...##...', '..####..', '..#..#..', '..####..', '.#...#..', '.#...#..'),
    'warden': ('.######.', '.#.##.#.', '.#.##.#.', '.#....#.', '.#.##.#.', '.######.', '.#....#.', '........'),
    'archivist': ('...##...', '..####..', '...##...', '.######.', '.#.##.#.', '.######.', '..#..#..', '..#..#..'),
    'breather': ('...##...', '..####..', '.#.##...', '..###.##', '...##...', '..####..', '..#..#..', '........'),
    'vapor': ('..#...#.', '...#.#..', '.#..#...', '..#...#.', '...#.#..', '.#..#...', '..#...#.', '........'),
    'pen': ('.....#..', '....##..', '...##...', '..##....', '.##.....', '.#......', '.#####..', '........'),
    'shirt': ('..#..#..', '.######.', '.######.', '..####..', '..####..', '..####..', '..####..', '........'),
    'medal': ('..#..#..', '..####..', '...##...', '..####..', '.##..##.', '.##..##.', '..####..', '........'),
    'tool': ('.#..#...', '.#..#...', '.####...', '..##....', '...##...', '....##..', '.....#..', '........'),
    'bag': ('..####..', '..#..#..', '.######.', '.#....#.', '.#.##.#.', '.#....#.', '.######.', '........'),
    'signs': ('...##...', '..#..#..', '.#....#.', '..#..#..', '...##...', '..#..#..', '.#....#.', '........'),
    'gear': ('..#..#..', '.######.', '..#..#..', '..####..', '..#..#..', '.######.', '..#..#..', '........'),
    'insight': ('..####..', '.#....#.', '.#.##.#.', '.#....#.', '..####..', '...##...', '..####..', '........'),
    'eye': ('........', '..####..', '.#.##.#.', '.#.##.#.', '..####..', '........', '........', '........'),
    'check': ('........', '.....#..', '....##..', '.#.##...', '.###....', '..#.....', '........', '........'),
    'log': ('.######.', '.#.#..#.', '.#.##.#.', '.#.#..#.', '.#.##.#.', '.#.#..#.', '.######.', '........'),
}

# 地图专用大轮廓槽（2026-10-18，docs/261018方案合集.md §7）。
# 同一语义键的地图图形另占一个大字面槽（命名空间 map:<symbol key>），只在地图
# 渲染里启用（symbols.map_symbol）；行内/右栏/图鉴继续用 ICONS 的常规回退字形。
# 独立波段 0xE2C0–0xE33F 固定给地图图标（128 槽），避免与物品家族（0xE240 起）抢槽。
# 每项：源字形（取自 SYMBOLS 的主题字形，单码位）、回退文字、拟合类别。
MAP_ICON_BAND = 0xE2C0
MAP_ICON_BAND_SIZE = 0x80
MAP_ICON_FIT = {
    # 类别 -> (外框最大宽, 外框最大高)，单位=字体 UPM 格子（1180 = 一格两列物理宽高）。
    # docs §7.5.C 的首轮设计目标：块状墙体 80–95%、特殊地板 60–80%、紧凑异象 75–90%；
    # fixture 是贴图式构件（箭头/排气口/隔屏等），尺寸由构图本身决定，不再整体缩放。
    'block': (1086, 1086),
    'floor': (920, 920),
    'anomaly': (1015, 1015),
    'fixture': (1080, 1080),
    'plant': (950, 950),
}


def _rotate_rects(rects, quarter_turns):
    """归一化矩形绕格心顺时针旋转 90°×n（x/y 均为 0..1、y 向下）。"""
    result = tuple(rects)
    for _ in range(quarter_turns % 4):
        result = tuple((1 - y1, x0, 1 - y0, x1) for (x0, y0, x1, y1) in result)
    return result


# 地图构件像素构图（2026-10-18 §7.6.2「需要专门构图而非统一放大的候选」）。
# 坐标是格子内的归一化矩形；glyph 是在格心叠加的矢量字形（箭头等），按列出的最大
# 宽高等比缩放（不拉伸）。这些构件本身已铺到目标体量，不再走包围盒整体放大。
_FRAME = ((0.04, 0.04, 0.96, 0.13), (0.04, 0.87, 0.96, 0.96),
          (0.04, 0.13, 0.13, 0.87), (0.87, 0.13, 0.96, 0.87))
_THIN_FRAME = ((0.03, 0.03, 0.97, 0.09), (0.03, 0.91, 0.97, 0.97),
               (0.03, 0.09, 0.09, 0.91), (0.91, 0.09, 0.97, 0.91))
_FAN_BLADES = ((0.17, 0.17, 0.30, 0.23), (0.17, 0.17, 0.23, 0.30),
               (0.70, 0.17, 0.83, 0.23), (0.77, 0.17, 0.83, 0.30),
               (0.17, 0.77, 0.30, 0.83), (0.17, 0.70, 0.23, 0.83),
               (0.70, 0.77, 0.83, 0.83), (0.77, 0.70, 0.83, 0.83))
_BELT_RAILS = ((0.15, 0.14, 0.23, 0.86), (0.77, 0.14, 0.85, 0.86))
MAP_SHAPES = {}
for _name, _glyph_char, _turns in (('fan_n', '↑', 0), ('fan_e', '→', 1),
                                   ('fan_s', '↓', 2), ('fan_w', '←', 3)):
    MAP_SHAPES[_name] = {'rects': _FRAME + _FAN_BLADES,
                         'glyph': (_glyph_char, 0.52, 0.52)}
for _name, _glyph_char, _turns in (('belt_n', '↑', 0), ('belt_e', '→', 1),
                                   ('belt_s', '↓', 2), ('belt_w', '←', 3)):
    MAP_SHAPES[_name] = {'rects': _THIN_FRAME + _rotate_rects(_BELT_RAILS, _turns),
                         'glyph': (_glyph_char, 0.42, 0.42)}
MAP_SHAPES['exhaust'] = {
    'rects': _FRAME + ((0.13, 0.28, 0.87, 0.35), (0.13, 0.65, 0.87, 0.72)),
    'glyph': ('⋘', 0.62, 0.62),
}
MAP_SHAPES['glass_screen'] = {
    'rects': ((0.16, 0.04, 0.26, 0.96), (0.74, 0.04, 0.84, 0.96),
              (0.16, 0.04, 0.84, 0.12), (0.16, 0.88, 0.84, 0.96),
              (0.34, 0.26, 0.66, 0.32), (0.34, 0.47, 0.66, 0.53),
              (0.34, 0.68, 0.66, 0.74)),
}
MAP_SHAPES['sleeper'] = {
    'rects': ((0.03, 0.39, 0.97, 0.61), (0.03, 0.33, 0.13, 0.67),
              (0.87, 0.33, 0.97, 0.67)),
}
MAP_SHAPES['moss_wall'] = {
    'dither': (0.04, 0.04, 0.96, 0.96),
    'cols': 12, 'rows': 12, 'density': 0.70,
    'extra_rects': ((0.04, 0.82, 0.96, 0.96),),
}
MAP_SHAPES['regret_anchor'] = {
    'rects': ((0.42, 0.04, 0.58, 0.08), (0.42, 0.16, 0.58, 0.20),
              (0.42, 0.08, 0.46, 0.16), (0.54, 0.08, 0.58, 0.16),
              (0.47, 0.20, 0.53, 0.82), (0.28, 0.28, 0.72, 0.34),
              (0.20, 0.64, 0.30, 0.70), (0.16, 0.70, 0.26, 0.82),
              (0.70, 0.64, 0.80, 0.70), (0.74, 0.70, 0.84, 0.82),
              (0.30, 0.82, 0.70, 0.88), (0.44, 0.88, 0.56, 0.96)),
}
MAP_SHAPES['alarm'] = {
    'rects': ((0.15, 0.36, 0.25, 0.64), (0.25, 0.30, 0.33, 0.70),
              (0.33, 0.22, 0.39, 0.78), (0.51, 0.34, 0.57, 0.66),
              (0.65, 0.24, 0.71, 0.76), (0.79, 0.14, 0.85, 0.86)),
}
MAP_SHAPES['book_cart'] = {
    'rects': ((0.12, 0.06, 0.22, 0.34), (0.24, 0.10, 0.34, 0.34),
              (0.36, 0.04, 0.46, 0.34), (0.48, 0.11, 0.56, 0.34),
              (0.08, 0.34, 0.92, 0.42),
              (0.10, 0.42, 0.18, 0.74), (0.82, 0.42, 0.90, 0.74),
              (0.18, 0.52, 0.82, 0.58), (0.10, 0.74, 0.90, 0.82),
              (0.20, 0.82, 0.34, 0.96), (0.66, 0.82, 0.80, 0.96)),
}

MAP_ICON_ROWS = (
    # 块状/网格特殊墙体（docs §7.3「优先修复的墙体与地板」）
    ('wall.condensing', '▦', 'block'),
    ('wall.reflective', '▣', 'block'),
    ('wall.absorbing', '▥', 'block'),
    ('wall.glass_curtain', '▩', 'block'),
    ('wall.hollow', '▢', 'block'),
    ('wall.cloud', '□', 'block'),
    ('wall.stone_platform', '▣', 'block'),
    ('wall.weeping_crystal', '▨', 'block'),
    ('wall.silent_stone', '▧', 'block'),
    ('wall.unconscious_crystal', '◲', 'block'),
    ('wall.mirror_lake', '◍', 'block'),
    ('wall.porcelain', '◈', 'block'),
    ('wall.cornstarch', '◇', 'block'),
    ('wall.movable_type', '≡', 'block'),
    ('wall.graphene', '⊞', 'block'),
    ('wall.idea_cube', '⊠', 'block'),
    ('wall.library.shelf', '▤', 'block'),
    # 特殊地板（同上表格）
    ('floor.ice', '◌', 'floor'),
    ('floor.checker', '⊞', 'floor'),
    ('floor.hollow', '⌀', 'floor'),
    # 紧凑型异象（docs §7.3「优先复核的异象」）
    ('anomaly.reverse_drummer', '◎', 'anomaly'),
    ('anomaly.clock_keeper', '⧗', 'anomaly'),
    ('anomaly.mirror_attendant', '⧉', 'anomaly'),
    ('anomaly.blank_rift', '□', 'anomaly'),
    ('anomaly.sunken_bell', '◕', 'anomaly'),
    ('anomaly.first_cry', 'ω', 'anomaly'),
    ('anomaly.folded_person', '\U00013020', 'anomaly'),
    ('anomaly.model_porter', '\U00013003', 'anomaly'),
    ('anomaly.stair_echo', '⌂', 'anomaly'),
    ('anomaly.silent_mirror', '⇧', 'anomaly'),
    ('anomaly.wet_choir', '♬', 'anomaly'),
    ('anomaly.thought_worm', '\U00013197', 'anomaly'),
    ('anomaly.nightmare_weaver', '❥', 'anomaly'),
    ('anomaly.primordial_impulse', '↯', 'anomaly'),
)

# 第二批（§7.6 顺序：先修轮廓偏小，再修细长构图）：异象统一放大 + 构件专门构图。
MAP_ICON_EXTRA = (
    ('anomaly.ticket_inspector', '\U00013005', 'anomaly'),
    ('anomaly.potted_keeper', '\U000131B0', 'anomaly'),
    ('anomaly.subtitle_group', '₩', 'anomaly'),
    ('anomaly.ink_bottle_guard', '⚘', 'anomaly'),
    ('anomaly.echo_door', '⋂', 'anomaly'),
    ('anomaly.null_witness', 'ø', 'anomaly'),
    ('anomaly.sleepless_watch', '\U0001302D', 'anomaly'),
    ('anomaly.silent_proofreader', '\U000133F2', 'anomaly'),
    ('anomaly.whole_choir', '⌇', 'anomaly'),
)

# 第三批（§7.6.2 尾项）：横向已满/细长/植物/气体纹理的专门构图。
# 宽异象优先提高最小笔画与高度，不再整体放大；植物用阅读字体原形按植物带放大；
# 气体三档用整格抖动纹理（保留 ░/▒/▓ 三档语义，只在两列地图档替换字形）。
MAP_SHAPES['paper_fish'] = {
    'rects': ((0.04, 0.30, 0.12, 0.50), (0.04, 0.50, 0.12, 0.70),
              (0.12, 0.40, 0.18, 0.60), (0.10, 0.38, 0.72, 0.62),
              (0.72, 0.42, 0.82, 0.58), (0.82, 0.46, 0.88, 0.54),
              (0.30, 0.22, 0.42, 0.38), (0.34, 0.62, 0.46, 0.78)),
}
MAP_SHAPES['nightmare_herder'] = {
    'rects': ((0.14, 0.08, 0.20, 0.92), (0.20, 0.08, 0.30, 0.14),
              (0.30, 0.14, 0.34, 0.22),
              (0.44, 0.28, 0.58, 0.38), (0.42, 0.38, 0.60, 0.68),
              (0.44, 0.68, 0.50, 0.90), (0.52, 0.68, 0.58, 0.90),
              (0.66, 0.48, 0.72, 0.54), (0.76, 0.50, 0.82, 0.56),
              (0.70, 0.60, 0.76, 0.66)),
}
MAP_SHAPES['projection_crew'] = {
    'rects': ((0.10, 0.66, 0.68, 0.78), (0.14, 0.34, 0.58, 0.66),
              (0.58, 0.44, 0.72, 0.58), (0.20, 0.14, 0.34, 0.20),
              (0.20, 0.14, 0.24, 0.34), (0.30, 0.14, 0.34, 0.34),
              (0.20, 0.30, 0.34, 0.34),
              (0.40, 0.14, 0.54, 0.20), (0.40, 0.14, 0.44, 0.34),
              (0.50, 0.14, 0.54, 0.34), (0.40, 0.30, 0.54, 0.34),
              (0.72, 0.38, 0.94, 0.43), (0.72, 0.57, 0.94, 0.62)),
}
MAP_SHAPES['long_take_director'] = {
    'rects': ((0.30, 0.22, 0.66, 0.48), (0.66, 0.30, 0.78, 0.42),
              (0.34, 0.12, 0.46, 0.24), (0.50, 0.12, 0.62, 0.24),
              (0.34, 0.24, 0.62, 0.28),
              (0.42, 0.48, 0.46, 0.92),
              (0.30, 0.48, 0.34, 0.62), (0.26, 0.60, 0.30, 0.74),
              (0.22, 0.72, 0.26, 0.84), (0.18, 0.84, 0.22, 0.94),
              (0.58, 0.48, 0.62, 0.62), (0.62, 0.60, 0.66, 0.74),
              (0.66, 0.72, 0.70, 0.84), (0.70, 0.84, 0.74, 0.94)),
}
MAP_SHAPES['oblivion_archivist'] = {
    'rects': ((0.42, 0.04, 0.58, 0.16), (0.38, 0.16, 0.62, 0.58),
              (0.34, 0.58, 0.66, 0.92), (0.18, 0.44, 0.34, 0.62),
              (0.18, 0.46, 0.22, 0.60), (0.66, 0.50, 0.82, 0.66),
              (0.66, 0.52, 0.70, 0.64)),
}
MAP_SHAPES['choir'] = {
    'rects': ((0.26, 0.06, 0.30, 0.18), (0.24, 0.18, 0.28, 0.34),
              (0.28, 0.34, 0.32, 0.50), (0.30, 0.50, 0.34, 0.66),
              (0.34, 0.66, 0.38, 0.84), (0.38, 0.84, 0.44, 0.94),
              (0.44, 0.06, 0.48, 0.20), (0.46, 0.20, 0.50, 0.38),
              (0.50, 0.38, 0.54, 0.56), (0.52, 0.56, 0.56, 0.72),
              (0.56, 0.72, 0.60, 0.90),
              (0.62, 0.08, 0.66, 0.22), (0.60, 0.22, 0.64, 0.40),
              (0.64, 0.40, 0.68, 0.58), (0.66, 0.58, 0.70, 0.76),
              (0.70, 0.76, 0.74, 0.94)),
}
MAP_SHAPES['unfinished_period'] = {
    'rects': ((0.30, 0.05, 0.70, 0.13), (0.22, 0.13, 0.30, 0.87),
              (0.70, 0.13, 0.78, 0.87), (0.30, 0.87, 0.70, 0.95),
              (0.34, 0.72, 0.66, 0.80)),
}
for _name, _density in (('gas_faint', 0.18), ('gas_mid', 0.45), ('gas_high', 0.78)):
    MAP_SHAPES[_name] = {
        'dither': (0.04, 0.04, 0.96, 0.96),
        'cols': 10, 'rows': 10, 'density': _density,
    }


MAP_SHAPE_ROWS = (
    # key, MAP_SHAPES 名, 类别, 回退字形（SYMBOLS 主题字形的首个字符）
    ('wall.hospital_exhaust', 'exhaust', 'fixture', '⋘'),
    ('wall.hospital_fan.n', 'fan_n', 'fixture', '↑'),
    ('wall.hospital_fan.e', 'fan_e', 'fixture', '→'),
    ('wall.hospital_fan.s', 'fan_s', 'fixture', '↓'),
    ('wall.hospital_fan.w', 'fan_w', 'fixture', '←'),
    ('floor.belt.n', 'belt_n', 'floor', '↑'),
    ('floor.belt.e', 'belt_e', 'floor', '→'),
    ('floor.belt.s', 'belt_s', 'floor', '↓'),
    ('floor.belt.w', 'belt_w', 'floor', '←'),
    ('wall.clinic.glass', 'glass_screen', 'fixture', '┈'),
    ('wall.sleeper', 'sleeper', 'fixture', '▬'),
    ('wall.moss_light', 'moss_wall', 'fixture', '▁'),
    ('wall.anchor_of_regret', 'regret_anchor', 'fixture', '⌐'),
    ('wall.alarm', 'alarm', 'fixture', '≫'),
    ('wall.library.cart', 'book_cart', 'fixture', '▰'),
)

# 统一规格（测试/脚本遍历用）：kind=outline 走阅读字体放大，kind=shape 走像素构图。
# 第三批新增槽位（追加在既有 58 槽之后，不重排旧码位）：
# 植物轮廓 + 横向/细长异象构图 + 气体三档整格纹理。
MAP_ICON_EXTRA_3 = (
    ('plant.mirror_orchid', '◈', 'plant'),
    ('plant.mint', '❃', 'plant'),
    ('plant.glass_shroom', '✱', 'plant'),
    ('plant.thorn_vine', '✽', 'plant'),
    ('plant.bubble_algae', '°', 'plant'),
    # 三位面专属 15 种（2026-10-26）：图片地图缩小时也要认得出是「哪一种」，
    # 不能 15 种共用一朵花的轮廓。
    ('plant.millennium.tape_tangle', '≋', 'plant'),
    ('plant.millennium.dial_reed', '♬', 'plant'),
    ('plant.millennium.contact_whisker', '⌁', 'plant'),
    ('plant.millennium.frame_shard', '▥', 'plant'),
    ('plant.millennium.frame_shard_flat', '▭', 'plant'),
    ('plant.millennium.heat_filament', '❈', 'plant'),
    ('plant.library.page_ridge', '▤', 'plant'),
    ('plant.library.page_ridge_flat', '▬', 'plant'),
    ('plant.library.binding_tangle', '⋈', 'plant'),
    ('plant.library.ink_wick', '▱', 'plant'),
    ('plant.library.blank_felt', '□', 'plant'),
    ('plant.library.abrasion_tabs', '▨', 'plant'),
    ('plant.hospital.suture_tangle', '⌘', 'plant'),
    ('plant.hospital.filter_tuft', '▦', 'plant'),
    ('plant.hospital.shutter_fold', '◧', 'plant'),
    ('plant.hospital.pressure_sac', '◔', 'plant'),
    ('plant.hospital.infusion_ampoule', '◖', 'plant'),
)

# 已有槽位改为专门构图时只替换该位置、不改变槽序/码位。
MAP_SHAPE_OVERRIDES = {
    'anomaly.whole_choir': ('choir', 'anomaly', '⌇'),
}

_SHAPE_ROWS_BY_KEY = {
    key: (shape, fit, source) for key, shape, fit, source in MAP_SHAPE_ROWS
}
_BASE_SPECS = []
for key, source, fit in MAP_ICON_ROWS + MAP_ICON_EXTRA:
    override = MAP_SHAPE_OVERRIDES.get(key)
    if override is not None:
        shape, fit, source = override
        _BASE_SPECS.append({'key': key, 'source': source, 'fit': fit,
                            'kind': 'shape', 'shape': shape})
    else:
        _BASE_SPECS.append({'key': key, 'source': source, 'fit': fit,
                            'kind': 'outline'})
for key, shape, fit, source in MAP_SHAPE_ROWS:
    _BASE_SPECS.append({'key': key, 'source': source, 'fit': fit,
                        'kind': 'shape', 'shape': shape})
_ADDITIONAL_SPECS = [
    {'key': key, 'source': source, 'fit': fit, 'kind': 'outline'}
    for key, source, fit in MAP_ICON_EXTRA_3
]
for key, shape, fit in (
    ('anomaly.paper_fish', 'paper_fish', 'anomaly'),
    ('anomaly.nightmare_herder', 'nightmare_herder', 'anomaly'),
    ('anomaly.projection_crew', 'projection_crew', 'anomaly'),
    ('anomaly.long_take_director', 'long_take_director', 'anomaly'),
    ('anomaly.oblivion_archivist', 'oblivion_archivist', 'anomaly'),
    ('anomaly.unfinished_period', 'unfinished_period', 'anomaly'),
    ('gas.faint', 'gas_faint', 'fixture'),
    ('gas.mid', 'gas_mid', 'fixture'),
    ('gas.high', 'gas_high', 'fixture'),
):
    source = {
        'anomaly.paper_fish': '𓆟', 'anomaly.nightmare_herder': '𓃭',
        'anomaly.projection_crew': '𓊵', 'anomaly.long_take_director': '𓎡',
        'anomaly.oblivion_archivist': '𓎛', 'anomaly.unfinished_period': '@',
        'gas.faint': '░', 'gas.mid': '▒', 'gas.high': '▓',
    }[key]
    _ADDITIONAL_SPECS.append({'key': key, 'source': source, 'fit': fit,
                              'kind': 'shape', 'shape': shape})
MAP_ICON_SPECS = tuple(_BASE_SPECS + _ADDITIONAL_SPECS)

# Explicit slots are permanent. Append within reserved bands; never reorder.
ICONS = {
    'player': {'codepoint': 0xE000, 'art': 'heart', 'fallback': '❤ '},
    'floor': {'codepoint': 0xE001, 'art': 'dot', 'fallback': '· '},
    'wall.door': {'codepoint': 0xE002, 'art': 'door', 'fallback': '╫ '},
    'wall.door.open': {'codepoint': 0xE003, 'art': 'door_open', 'fallback': '/ '},
    'wall.door.locked': {'codepoint': 0xE004, 'art': 'door_lock', 'fallback': '+ '},
    'wall.clinic.partition': {'codepoint': 0xE040, 'art': 'partition', 'fallback': '▯ '},
    'wall.clinic.bench': {'codepoint': 0xE041, 'art': 'table', 'fallback': '▱ '},
    'wall.clinic.tank': {'codepoint': 0xE042, 'art': 'sink', 'fallback': '◫ '},
    'wall.terracotta': {'codepoint': 0xE043, 'art': 'brick', 'fallback': '♜ '},
    'wall.copper_mesh': {'codepoint': 0xE044, 'art': 'mesh', 'fallback': '⌘ '},
    'wall.wood_table': {'codepoint': 0xE045, 'art': 'table', 'fallback': '▤ '},
    'floor.moon': {'codepoint': 0xE0C0, 'art': 'moon', 'fallback': '☉ '},
    'floor.pressure': {'codepoint': 0xE0C1, 'art': 'plate', 'fallback': '⊞ '},
    'floor.piezo': {'codepoint': 0xE0C2, 'art': 'electrode', 'fallback': '◉ '},
    'floor.insulation': {'codepoint': 0xE0C3, 'art': 'insulation', 'fallback': '◎ '},
    'floor.page': {'codepoint': 0xE0C4, 'art': 'page', 'fallback': '▸ '},
    'gas.hypno': {'codepoint': 0xE0C5, 'art': 'vapor', 'fallback': '◌ '},
    'gas.library.ink_mist': {'codepoint': 0xE0C6, 'art': 'vapor', 'fallback': '≈ '},
    'carried_hand': {'codepoint': 0xE100, 'art': 'pen', 'fallback': '✎ '},
    'carried_surface': {'codepoint': 0xE101, 'art': 'shirt', 'fallback': '♖ '},
    'carried_dependent': {'codepoint': 0xE102, 'art': 'medal', 'fallback': '⚜ '},
    'carried_habit': {'codepoint': 0xE103, 'art': 'tool', 'fallback': '⚒ '},
    'plant.mushroom': {'codepoint': 0xE180, 'art': 'mushroom', 'fallback': '♧ '},
    'plant.moon_shroom': {'codepoint': 0xE181, 'art': 'moon_shroom', 'fallback': '☾ '},
    'plant.hollow_shroom': {'codepoint': 0xE182, 'art': 'hollow_shroom', 'fallback': '◒ '},
    'hospital.sporebud': {'codepoint': 0xE183, 'art': 'sporebud', 'fallback': '♧ '},
    'plant.night_queen': {'codepoint': 0xE184, 'art': 'flower', 'fallback': '✾ '},
    'plant.whisper_fern': {'codepoint': 0xE185, 'art': 'fern', 'fallback': '✾ '},
    'plant.lily': {'codepoint': 0xE186, 'art': 'lily', 'fallback': '♪ '},
    'anomaly.faceless_watchman': {'codepoint': 0xE187, 'art': 'faceless', 'fallback': '☃ '},
    'anomaly.cooling_doll': {'codepoint': 0xE188, 'art': 'doll', 'fallback': '♟ '},
    'anomaly.silent_audience': {'codepoint': 0xE189, 'art': 'audience', 'fallback': '♙ '},
    'anomaly.door_warden': {'codepoint': 0xE18A, 'art': 'warden', 'fallback': '⌸ '},
    'anomaly.ink_archivist': {'codepoint': 0xE18B, 'art': 'archivist', 'fallback': '▤ '},
    'anomaly.fog_breather': {'codepoint': 0xE18C, 'art': 'breather', 'fallback': '≋ '},
    'nav.inventory': {'codepoint': 0xE200, 'art': 'bag', 'fallback': '▣ '},
    'nav.portents': {'codepoint': 0xE201, 'art': 'signs', 'fallback': '◈ '},
    'nav.equipment': {'codepoint': 0xE202, 'art': 'gear', 'fallback': '▼ '},
    'nav.insights': {'codepoint': 0xE203, 'art': 'insight', 'fallback': '◆ '},
    'nav.catalog': {'codepoint': 0xE204, 'art': 'eye', 'fallback': '◉ '},
    'nav.actions': {'codepoint': 0xE205, 'art': 'check', 'fallback': '✔ '},
    'nav.tasks': {'codepoint': 0xE206, 'art': 'log', 'fallback': '☷ '},
}


from .item_icons import ITEM_FAMILIES
for _name, (_point, _source, _fallback, _meaning) in ITEM_FAMILIES.items():
    ICONS['item.' + _name] = {
        'codepoint': _point, 'art': 'item.' + _name,
        'fallback': _fallback, 'source_character': _source,
    }

# 地图大轮廓槽：显式码位固定，不随追加重排（见上方 MAP_ICON_SPECS 注释）。
for _offset, _spec in enumerate(MAP_ICON_SPECS):
    _entry = {
        'codepoint': MAP_ICON_BAND + _offset,
        'art': 'map.' + _spec['key'],
        'fallback': _spec['source'] + ' ',
        'source_character': _spec['source'],
        'map_fit': _spec['fit'],
        'map_shape': _spec.get('shape'),
    }
    ICONS['map:' + _spec['key']] = _entry

# The expansion keeps its own append-only PUA band. These glyphs are backed by
# a per-codepoint font registration in catalog.json rather than the legacy
# family aliases above.
from .expansion.catalog import ENTRIES as _EXPANSION_ENTRIES
for _entry in _EXPANSION_ENTRIES:
    ICONS[_entry['icon_key']] = {
        'codepoint': _entry['icon_codepoint'],
        'art': 'expansion.' + _entry['id'],
        'fallback': _entry['terminal_fallback'],
        'ascii_fallback': _entry['ascii_fallback'],
        'source_character': _entry['source_character'],
        'source_kind': _entry['source_kind'],
        'source_codepoint': _entry['source_codepoint'],
        'source_font': _entry['source_font'],
        'source_family': _entry['source_family'],
        'source_font_sha256': _entry['source_font_sha256'],
        'license_key': _entry['license_key'],
    }


def icon_text(key):
    return set_cell_size(chr(ICONS[key]['codepoint']), 2)


def game_icon(key):
    """Only the dedicated launcher config guarantees that this font is loaded."""
    if env_flag('ICONS') and key in ICONS:
        return icon_text(key)
    return None


def map_icon(key):
    """地图专用大轮廓图标（2026-10-18 §7）：行内/图鉴不走这里。"""
    if not env_flag('ICONS'):
        return None
    slot = ICONS.get('map:' + key)
    if slot is None:
        return None
    return icon_text('map:' + key)
