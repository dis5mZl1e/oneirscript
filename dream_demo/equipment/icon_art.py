"""Absolute artwork for all current board equipment definitions.

Hand-designed canonical patterns; unrelated to spawn order, instance ID,
rarity, language or combat values. Dots are real holes, never painted cells.
Each symbol paints two terminal columns; geometry is still item_shapes.py.
Palette: body, highlight, accent. 0/1/2 are solid, 3/4/5 are split swatches.

字符通道（2026-10-10 图案规范）：pattern 里 `0-5` 与 `.` 保持旧语义
（纯色块/空洞），**其余任意 Unicode/ASCII 字符**渲染为前景字形——
底色取 body、前景色默认 light，出现在 ``accent_glyphs`` 里的字符用
accent 色（特征识别点必须一眼读到）。宽字形（终端两列）独占整格。
见 docs/perf-move-diagnosis-and-board-ux-plan.md §4。
"""
from dataclasses import dataclass
from functools import lru_cache

from rich.cells import cell_len


@dataclass(frozen=True)
class EquipmentArt:
    palette: tuple[str, str, str]
    pattern: str
    motif: str
    # 这些字符作为前景字形时用 accent 色（特征字符）；其余字形用 light。
    accent_glyphs: str = ""


def _art(body, light, accent, pattern, motif, accent_glyphs=""):
    return EquipmentArt((body, light, accent), pattern, motif, accent_glyphs)


EQUIPMENT_ART = {
    "paper_handle_letterknife": _art("#7c725d", "#e5dcc0", "#94a3a6", "▤╞═»", "旧信纸柄与拆信尖", "▤»"),
    "frayed_sleeve": _art("#657d81", "#d4e1dc", "#a7baa0", "║./║./╰╡", "透薄布纹与磨开的袖口", "╡"),
    "broken_tooth_thimble": _art("#686d83", "#dce2eb", "#92bfd0", "╥▥", "缺齿顶针与卡住的蓝线", "▥"),
    "ember_crayon": _art("#8c6651", "#edcc9a", "#f4a563", "▤▒▒═»", "发软纸套与留火蜡芯", "»"),
    "carbon_copy_knife": _art("#72748c", "#d9d9ec", "#8870bc", "▓╞══»", "双道复写刃", "»"),
    "door_hinge": _art("#a68846", "#e6cf82", "#695436", ".╥./╞█╡/.╨.", "黄铜轴心与齿瓣", "╥"),
    "echo_ring": _art("#6c859b", "#d4e9f5", "#84bdc6", "╭─╮/│.│/╰─╯", "冷银框与回声嵌点", ""),
    "rusty_boxcutter": _art("#8a5946", "#e2d9c4", "#c88c57", "▙▓»", "锈柄与亮刃", "»"),
    "binder_clip_launcher": _art("#465163", "#c5d5de", "#f1b454", "»./│./╰▓", "夹口与黄铜铰链", "»"),
    "voice_recorder_pen": _art("#466f68", "#b0ddd1", "#edbc66", "°▓▓»", "录音灯与笔身", "°"),
    "focusing_lens": _art("#3c6981", "#bce9ec", "#e8c76d", "╭─╮/├*┤/▓..", "金环聚光镜面", "*"),
    "dream_tapir_flute": _art("#65784e", "#c8d99b", "#d4aa74", "╷.╷/╰┼╯", "木管与三孔", "┼"),
    "pendulum_blade": _art("#74759a", "#dfdaf0", "#c7a569", "╭──╮/│▓▓»", "钟摆配重与弧刃", "»"),
    "null_pen": _art("#65576f", "#dac9d8", "#cc718b", "╻▓▓'", "空白笔芯与消隐尖", ""),
    "waxed_raincoat": _art("#58726c", "#b4c8a2", "#e4bf6c", "▓...▓/║...║/╠╦╩╦╣", "蜡黄门襟与青灰雨衣", "╦"),
    "lead_lined_apron": _art("#535e6b", "#9fb2bb", "#d0b67b", "╒╤╕/▓█▓/╘╪╛", "铅衬垂带", "╪"),
    "static_poncho": _art("#595788", "#c9c5ed", "#8fd2eb", "╷.╷/~▓~/▓../▒▓.", "折线电纹披风", "~"),
    "metronome_pendant": _art("#796341", "#dbc185", "#e88c68", "╒╕/╞╡/╷.", "摆针刻度", "╷"),
    "surveyor_compass": _art("#526f79", "#c0dfd3", "#efb66b", "╞╡/╥╨", "测绘十字指针", "╥"),
    "lucky_clover": _art("#4d795c", "#b9d88a", "#dbc55d", ".╬./╬*╬/.╬.", "四叶与金脉", "*"),
    "insulated_gloves": _art("#596e74", "#acc9cb", "#e7c66b", "▓.▓/╰╯╰", "绝缘指套与橡胶袖口", ""),
    "multitool_knife": _art("#465b70", "#c7d8e5", "#d79770", "▓../▓../╠╦╣", "折叠工具的多刃柄", "╦"),
    "stethoscope": _art("#496f76", "#bad8dc", "#ad819f", "╷.../│.../│.../╰═»°", "听诊软管与膜片", "»"),
    "echo_emitter": _art("#4d6e8b", "#b7d7f3", "#b198cf", "╞═╡/°°°", "对称回声栅与声波", "°"),
    "line_projector": _art("#4e7775", "#b5e4cf", "#e1b273", ".╷╷/.║║/╞═.", "光轴与投影格", "╞"),
    "headphone_coil": _art("#626a87", "#c2cee6", "#88baa5", "╒═╕/▓.▓/╘═╛", "双耳罩线圈", "═"),
    "unfinished_editor": _art("#755e81", "#d6c4dd", "#d89b81", ".╒╕/.~│/╞═.", "未闭合校改色带", "~"),
    "quiet_ticket": _art("#9d9c7e", "#e4e2c2", "#6f8c8d", "═╡°", "安静票根的打孔带", "°"),
    "bent_hook": _art("#866b54", "#d4ba93", "#a7c2c0", "╷./│./╰█", "弯钩与磨亮端头", "╷"),
    "single_earphone": _art("#586c90", "#c2d9ee", "#b79f74", "╭┬╮/.║.", "单侧耳塞与细柄", "┬"),
    "broken_watch": _art("#80715d", "#d7c5a1", "#b77a82", "╭╮/╞╡/╷.", "断裂表盘与红针", "╷"),
    "lighthouse_lens": _art("#546e87", "#d3e9e8", "#f0cf79", "╭─╮/│*│/▓..", "灯塔镜片的金色中心", "*"),
    "sketch_gloves": _art("#637993", "#c9d9ec", "#ca9cc8", "╷.╷/╰╤╯", "蓝铅笔指尖与草图袖边", "╤"),
    "gravestone_wristband": _art("#626c70", "#bbc7c2", "#a690bf", "█╪/╪█", "石带对角与紫色碑纹", "╪"),
    "hourglass_pendant": _art("#7a6d54", "#e0d2a7", "#abcee0", ".╤╡/╞╧.", "沙漏双锥与上行沙粒", "╤╧"),
    "high_pressure_pump": _art("#426e79", "#b9e3e4", "#d7a85e", "╒═╤╕/.║../.║..", "泵头、压力芯与阀柄", "╤"),
    "air_concentrator": _art("#65828d", "#d2e6df", "#b4a1d1", "╓../╟../╰»»", "气罐箍线与聚流嘴", "»"),
    "water_gun": _art("#356f97", "#a8ddf1", "#e5c268", "╓../╙../╰»»", "水箱、金阀与蓝色喷口", "»"),
    "hair_dryer": _art("#8d6566", "#e5c8b9", "#ebad65", "╒══╕/.╫../.║..", "暖风格栅与握柄", "═╫"),
    "nail_gun": _art("#666d79", "#c8d4dd", "#d68b62", "╞╤╤╡/▓»»▓", "钉仓与撞针", "»"),
    "sonic_whistle": _art("#638899", "#d0e5ea", "#cfa0cf", "╞°»", "声波哨的共鸣口", "°"),
    "dart_gun": _art("#567b69", "#c5d8ba", "#dc9974", "╥./║./╰»", "准星、枪管与镖仓", "»"),
    "ignite_gloves": _art("#9e5745", "#f0cd82", "#e78352", "~.~/▓▓▓", "燃烧指尖与余温掌心", "~"),
    "phoenix_robe": _art("#963e51", "#f2cd85", "#e27753", "╒══╕/│~~│/▓▓▓▓", "金羽肩饰与绯红火尾", "~"),
    "blast_ring": _art("#896343", "#ebc88d", "#ed815c", "╭┼╮/│.│/╰┼╯", "爆裂嵌珠与铜环", "┼"),
    "arsonist_watch": _art("#8c5447", "#e1c085", "#ef995c", "╭╮/╞╡/╷.", "引火红针与铜表壳", "╷"),
    "pen_sharp": _art("#606877", "#d8e0e1", "#bda77a", "╞═╡»", "硬笔握节与锋尖", "»"),
    "heavy_stapler": _art("#606d66", "#becfc1", "#c39579", "111/╞╪╡", "厚压板与出针口", "╪"),
    "rift_shears": _art("#675287", "#d2bce9", "#88d5d4", "╲│╱/─┼─/╫..", "交叉剪刃与裂隙铰心", "┼"),
    "patched_pajamas": _art("#67798e", "#b7ccd6", "#ce9b9b", "▓.▓/░▒░/▓../░▒.", "异色补丁与睡衣布面", "▒"),
    "leather_apron": _art("#895d49", "#d8ab7f", "#acb19c", "╷.╷/│.│/╰┼╯", "皮带与缝线下摆", "┼"),
    "lucky_coin": _art("#a08042", "#ecd394", "#829974", "╭╮/╰¤", "磨亮币缘与幸运币纹", "¤"),
    "night_battery": _art("#515677", "#aab9d8", "#ab91ce", "╒╤╕/│█│", "夜蓝电池与紫色芯", "█"),
    "warm_gloves": _art("#9c6c68", "#edc8b0", "#dfb273", "▓.▓/░░░", "暖绒手套与针织掌纹", "░"),
    "screwdriver": _art("#9a6353", "#d5dedb", "#daaa64", "▓▓═»", "橙柄与钢杆", "»"),
    "wax_seal": _art("#a34e63", "#edb0b7", "#d8bd79", "╭╮/││/✦.", "章柄与四芒蜡纹", "✦"),
    "first_cry_fang": _art("#817394", "#e8dce7", "#cf85a7", "╷../╷../╰▟▟▟", "初啼牙冠与淡红牙根", "▟"),
    "lightless_cloak": _art("#474c69", "#9da7c2", "#ad8eba", "╭──╮/│░░│/▒▓..", "无光披褶与黯紫内衬", ""),
    "void_pendant": _art("#49435e", "#b7adc9", "#6fa6b7", "╭─╮/│█│/╰..", "空洞吊坠与青色边光", ""),
    "fate_coin": _art("#8c7293", "#dfcbe3", "#d7b877", "╭─╮/╰╥╯", "双色币面与命运轴", "╥"),
    "deep_thought_chisel": _art("#576580", "#c7d6e6", "#9ab4ab", "╷.../│.../│.../╰»»»", "凿刃与沉思刻度", "»"),
    "rift_wax_seal": _art("#755397", "#d5bae7", "#8cd9cf", "╭┼╮/│││/╰..", "裂印蜡章与青色断缝", "┼"),
    "dreamweaver_gloves": _art("#806898", "#dec9eb", "#82c6c4", "╷.╷/║.║/╬╬╬", "织梦经纬与银指尖", "╬"),
    "swift_thought_ring": _art("#517888", "#c5e3e5", "#d6bf71", "╭┤╮/│.│/╰├╯", "迅思环的斜向流线", "┤├"),
    "prism_pendant": _art("#667e98", "#d5e2ee", "#c895cc", ".╥./3█4/.5.", "棱镜的三色折面", "╥"),
    "salt_soaked_coil": _art("#578683", "#d3e5cf", "#bfa4da", "╭┬╮/│.│/╰┴╯", "盐晶镶点与湿铜线圈", "┬┴"),
    "ember_boots": _art("#86584d", "#dbbb8c", "#ee9163", ".▓▓/.░░/╰╰.", "余火鞋面与乌黑鞋底", "░"),
    "hunting_lanyard": _art("#77774f", "#d1d4a0", "#c48879", "╷../│../╰»»", "猎绳结与红色挂签", "»"),
    "split_tuning_fork": _art("#656b8d", "#d1d7ea", "#b797d0", "╷┬╷/.╰.", "双音叉尖与紫色共鸣柄", "┬"),
    "blank_half_page": _art("#9d9b89", "#ece7d0", "#a29fbd", ".▓▓/░░.", "半页留白与折痕", "░"),
    "blank_cheque_book": _art("#82998e", "#dde8d6", "#bea987", "╒═╕/111", "装订金边与空白票页", "═"),
    "faded_id_card": _art("#78868c", "#d1d5cd", "#b596a0", "▓╌/╌░", "证件照与褪色信息条", "░"),
    "paper_clip": _art("#667e8a", "#d1e1e4", "#a4b3ca", "╷.╷/╰┬╯", "纸夹双弯与金属搭口", "┬"),
    "singed_gloves": _art("#695650", "#bba18a", "#d89162", "█.█/░▓░", "焦黑指尖与烧痕掌面", "░"),
    "model_screw": _art("#7a8b82", "#d8e4d7", "#bd9c6b", "╞═»", "螺纹节与铜头", "»"),
    "stair_bolt": _art("#6b7983", "#ccdce2", "#b7a076", "╷./║./╞═", "台阶螺杆与压帽", "╷"),
    "tape_measure": _art("#ab8948", "#f0dca0", "#728c9b", "╓╞/╙═", "卷尺壳与拉出的尺带", "╞═"),
    "sling": _art("#87745a", "#d8c5a1", "#93a9a5", ".»~/╰─.", "投石绳与皮兜", "»"),
    "throwing_gloves": _art("#567c70", "#badbba", "#d8b176", "╷.╷/╞╡╞", "投掷指套与固定掌带", "╞╡"),
    "focus_ring": _art("#59649b", "#c1d2f0", "#d4b984", "╷.╷/╰┼╯", "准星指节与铜色锁环", "┼"),
    "unread_99": _art("#8d4c5d", "#f4bcc0", "#ea6b67", "°▓/▓╌", "未读红点与消息栏", "°"),
    "crystal_charm": _art("#548598", "#d0f1ef", "#c5a5dc", "╱╲/╲╱", "水晶机箱挂饰的冷色折面", ""),
    "broadband_grail": _art("#a48746", "#f2dfa2", "#85c9aa", "╒╕/╰*", "宽带杯口与绿光杯腹", "*"),
    "glass_bottle": _art("#4b7f90", "#d2eef0", "#86c8db", "╻╷/▓~", "玻璃瓶颈与蓝色液面", "~"),
    "ideal_tube": _art("#536d91", "#d4dcf1", "#aeb8da", "╻╻/║~", "试管隔腔与淡紫液面", "~"),
    "balloon": _art("#9a5266", "#f1becf", "#d888a0", "╭╮/╰╿", "气球圆面与扎口", "╿"),
    "ideal_vessel": _art("#667c70", "#d6e9ce", "#c7b788", "╤╤/╧*", "层叠气室与金色阀门", "*"),
}


def _colors(palette, symbol):
    body, light, accent = palette
    return {
        "0": (body, body), "1": (light, light), "2": (accent, accent),
        "3": (body, accent), "4": (accent, body), "5": (body, light),
    }[symbol]


@lru_cache(maxsize=512)
def painted_cells(definition_id, rotation=0):
    """Return immutable local (x, y, left, right, glyphs) cells.

    ``glyphs = (left_glyph, left_fg, right_glyph, right_fg)``：前景为 "" 时
    该列渲染纯背景色块（旧 0-5 语义，兼容存量图案）；窄字形占左列、右列
    补背景；宽字形（终端两列，cell_len==2）独占整格，右列 fg 记 None。
    """
    if rotation not in (0, 90, 180, 270):
        raise ValueError("Artwork supports the same four rotations as equipment")
    art = EQUIPMENT_ART.get(definition_id)
    if art is None:
        from .item_shapes import shape_for
        from .shapes import occupied_cells
        return tuple((x, y, "#8c96a8", "#c5a778", ("", "", "", ""))
                     for x, y in occupied_cells(shape_for(definition_id), rotation, 0, 0))
    body, light, accent = art.palette
    cells = []
    for y, row in enumerate(art.pattern.split("/")):
        for x, symbol in enumerate(row):
            if symbol == ".":
                continue
            if symbol in "012345":
                left, right = _colors(art.palette, symbol)
                cells.append((x, y, left, right, ("", "", "", "")))
                continue
            fg = accent if symbol in art.accent_glyphs else light
            if cell_len(symbol) == 2:
                cells.append((x, y, body, body, (symbol, fg, "", None)))
            else:
                cells.append((x, y, body, body, (symbol, fg, "", "")))
    for _ in range(rotation // 90):
        max_y = max(y for _, y, *_ in cells)
        cells = [(max_y - y, x, left, right, glyphs)
                 for x, y, left, right, glyphs in cells]
    min_x = min(x for x, *_ in cells)
    min_y = min(y for _, y, *_ in cells)
    return tuple(sorted((x - min_x, y - min_y, left, right, glyphs)
                        for x, y, left, right, glyphs in cells))

EQUIPMENT_ART.update({
    "hospital.suture_shears": _art("#376278", "#eefaff", "#78cabb", '╷./╰×', '不闭合的手术剪'),
    "hospital.hollow_lancet": _art("#376278", "#eefaff", "#78cabb", '╞»', '空心针'),
    "hospital.suture_coil": _art("#a78e9b", "#fff2f8", "#d4b6c6", '╷.╷/╰═╯', '缝合线圈'),
    "hospital.lymph_filter": _art("#39786f", "#ebfff5", "#83c5df", '╭╮/╰╯', '淋巴滤环'),
    "hospital.cerebral_ampoule": _art("#35869a", "#edffff", "#a4dce9", '╥/║/╨', '脑脊安瓿'),
    "hospital.sterile_glove": _art("#579895", "#e9ffff", "#b6e8dc", '╷╷╷/.╧.', '无垢手套'),
    "hospital.glass_rib": _art("#687d91", "#f4f9ff", "#b5cad4", '.╭╮/╰╯.', '玻璃肋'),
    "hospital.pulse_tag": _art("#438977", "#edfff3", "#e1c789", '♥╡', '心搏标签'),
    "hospital.marrow_spoon": _art("#757e88", "#ffffff", "#c0c9d4", '╷./╰○', '骨髓银匙'),
    "hospital.lumen_mask": _art("#47779b", "#ffffff", "#a6dcf3", '╭╮/◉◉/╵.', '白昼面罩'),
})

EQUIPMENT_ART.update({
    "library.bookmark": _art("#675244", "#f5e9c4", "#9bb9ab", '╥/║/∨', '书签'),
    "library.index": _art("#675244", "#f5e9c4", "#9bb9ab", '╔╤/╚═', '索引卡'),
    "library.fold": _art("#675244", "#f5e9c4", "#9bb9ab", '╷./╰◢', '折页'),
    "library.paperweight": _art("#675244", "#f5e9c4", "#9bb9ab", '.╭▓/▓╯.', '纸镇'),
    "library.lens": _art("#675244", "#f5e9c4", "#9bb9ab", '╭◉/◉╯', '阿莱夫透镜'),
    "library.quill": _art("#675244", "#f5e9c4", "#9bb9ab", '╱╱»', '羽笔'),
    "library.card": _art("#675244", "#f5e9c4", "#9bb9ab", '╠▤', '借阅证'),
    "library.testimony": _art("#675244", "#f5e9c4", "#9bb9ab", '▒╤▒/.╵.', '残页'),
})
