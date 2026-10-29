from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from .cell_size import set_cell_size
from .data.icon_glyphs import game_icon, map_icon, ICONS, icon_text
from .env_compat import LEGACY_PREFIX, NEW_PREFIX, flag as _env_flag

# ---- ICONS 开关的热路径（2026-10-27 A4）------------------------------------
# 地图一帧 800+ 格都要经过 symbol()/map_symbol() → game_icon()/map_icon()，而
# 两者每次都走 env_compat.flag('ICONS') → os.environ.get：实测 get('ICONS')
# ≈1.0µs/次（os.environ 的 __getitem__ 要 encodekey + 解码），一次动作 3372 次
# 环境读取绝大多数出在这里（docs/2026-10-27-action-hotpath-profile.md §7）。
#
# 这里只把「开关读取」换成 os.environ 同一份数据表上的两次普通 dict 查找
# （实测 ≈0.07µs），**仍然每次调用现读活环境**——monkeypatch.setenv /
# os.environ[name]=v 写的正是这张表，所以 ONEIRSCRIPT_ICONS / DREAM_STRATA_ICONS
# 的运行时切换依旧立即生效，不做任何跨帧缓存。字形解析仍复用
# icon_glyphs.icon_text，ICONS 表本身的变化也立即生效。
_ENV_DATA = getattr(os.environ, "_data", None)
_ENV_DATA_IS_TEXT = bool(
    isinstance(_ENV_DATA, dict)
    and all(isinstance(key, str) for key in list(_ENV_DATA)[:1])
)
_ICONS_ENV_NEW = NEW_PREFIX + "ICONS"
_ICONS_ENV_LEGACY = LEGACY_PREFIX + "ICONS"
_TRUTHY_FLAGS = ("1", "true", "yes", "on")


def themed_icons_enabled() -> bool:
    """env_compat.flag('ICONS') 的等价热路径版（每次调用现读活环境）。

    语义与 env_compat.flag 逐字一致：新名优先、旧名回退、都没有按 False、
    真值集合相同。取不到 os.environ._data（非 CPython / 私有字段消失）时
    回退到 env_compat.flag，行为不变。
    """
    data = _ENV_DATA if _ENV_DATA_IS_TEXT else None
    if data is None:
        return _env_flag("ICONS")
    value = data.get(_ICONS_ENV_NEW)
    if value is None:
        value = data.get(_ICONS_ENV_LEGACY)
    if value is None:
        return False
    return value.strip().lower() in _TRUTHY_FLAGS


def themed_icon(key: str) -> str | None:
    """icon_glyphs.game_icon(key) 的等价热路径版。

    仅替换开关读取这一笔固定开销；key 是否存在、图标字形如何解析都与
    game_icon 完全一致（等价性由 tests/test_hotpath_micro_261027.py 逐键断言）。
    """
    if not _ENV_DATA_IS_TEXT:
        return game_icon(key)
    if key not in ICONS or not themed_icons_enabled():
        return None
    return icon_text(key)


def themed_map_icon(key: str) -> str | None:
    """icon_glyphs.map_icon(key) 的等价热路径版（键前缀 map:）。"""
    if not _ENV_DATA_IS_TEXT:
        return map_icon(key)
    slot = "map:" + key
    if slot not in ICONS or not themed_icons_enabled():
        return None
    return icon_text(slot)


@dataclass(frozen=True)
class SymbolDef:
    themed: str
    ascii: str


SYMBOLS: dict[str, SymbolDef] = {
    # 玩家：文本心形+空格。不用 ❤️（U+2764+FE0F emoji 序列）——rich 按 2 列
    # 布局，但经典控制台（conhost/PowerShell 直启）把该序列渲染为 1 列，
    # 导致玩家格右侧整行错位、鼠标点击错位。'❤ ' 两类终端一致为 2 列。
    "player": SymbolDef("❤ ", "@@"),
    "floor": SymbolDef("· ", ".."),
    "solid": SymbolDef("██", "##"),
    "wall.hospital_exhaust": SymbolDef("⋘⋘", "EX"),
    "wall.clinic.partition": SymbolDef("▯▯", "WP"),
    "wall.clinic.cleanse": SymbolDef("⬒⬒", "CW"),
    "wall.clinic.light": SymbolDef("☁☁", "LW"),
    "wall.clinic.glass": SymbolDef("┈┈", "GW"),
    "wall.clinic.tank": SymbolDef("◫◫", "TK"),
    "wall.clinic.bench": SymbolDef("▱▱", "TB"),
    "wall.clinic.case": SymbolDef("⬚⬚", "RX"),
    "wall.clinic.cart": SymbolDef("⊡⊡", "HC"),
    "wall.hospital_fan.n": SymbolDef("↑↑", "^F"),
    "wall.hospital_fan.e": SymbolDef("→→", ">F"),
    "wall.hospital_fan.s": SymbolDef("↓↓", "vF"),
    "wall.hospital_fan.w": SymbolDef("←←", "<F"),
    "wall.compacted": SymbolDef("██", "##"),
    # 玻璃幕墙：▩ (U+25A9) 为几何图形区的双宽字符，rich 与经典控制台一致按 2 列渲染。
    "wall.glass_curtain": SymbolDef("▩▩", "GG"),
    "wall.reflective": SymbolDef("▣▣", "[]"),
    "wall.absorbing": SymbolDef("▥▥", "::"),
    "wall.condensing": SymbolDef("▦▦", "%%"),
    "wall.fuel": SymbolDef("╳╳", "XX"),
    "wall.deliquescent": SymbolDef("▟▟", "PP"),
    "wall.wax": SymbolDef("◒◒", "WW"),
    "wall.porcelain": SymbolDef("◈◈", "QQ"),
    "wall.hollow": SymbolDef("▢▢", "HH"),
    # 墙体符号一律写满两列：这些字形（≡ ⚱ ▉ ❄ ✦ ╥ ▬ ☁ ※ ∴）与 █ 同属
    # EAW=A，rich cell_len 单字符计 1、双写计 2，实测与 ██ 完全一致，
    # 因此「重复一次」既填满格子又不会破坏行对齐（旧写法「字形 + 空格」
    # 会在墙体右半边留白，看起来像没占满的残缺格子）。
    # 容器图标：按玩家要求回退为之前的 ⚱ / 🛢（去变体选择符，避免宽度错位）。
    "wall.movable_type": SymbolDef("≡≡", "TT"),
    "wall.memory_vessel": SymbolDef("⚱ ", "MM"),
    "wall.thought_vessel": SymbolDef("🛢 ", "NN"),
    "wall.hardened": SymbolDef("▊▊", "HA"),
    "wall.clarity_stone": SymbolDef("❄ ", "CL"),
    "wall.dream_crystal": SymbolDef("✦✦", "MJ"),
    # §12 F：三种新增环境设施（2026-10-20）。字形守则：两列几何/装饰符，
    # ascii 缩写全表唯一（DL/AC/AM 均未被占用）。
    "wall.dream_niche_lamp": SymbolDef("❍❍", "DL"),
    "wall.arc_lamp_rig": SymbolDef("⊛⊛", "AC"),
    "wall.ember_lamp": SymbolDef("✹✹", "AM"),
    "wall.candle_pillar": SymbolDef("╥╥", "ZZ"),
    "wall.sleeper": SymbolDef("▬▬", "XM"),
    "wall.cloud": SymbolDef("□□", "YK"),
    "wall.millet": SymbolDef("※ ", "HL"),
    "wall.ash": SymbolDef("∴∴", "HJ"),
    # 无意识领域（21–27）：致密聚合物用「█▉」（整块+7/8块，内部无缝）
    # 读作一个 2 宽实心方块——四个「█」并排在不同色下会露出字间细缝。
    "wall.dense": SymbolDef("█▉", "DD"),
    "wall.nightmare_rock": SymbolDef("▉▉", "NR"),
    "wall.weeping_crystal": SymbolDef("▨▨", "WC"),
    "wall.iron_curtain": SymbolDef("║║", "IC"),
    "wall.lightless_velvet": SymbolDef("▞▞", "LV"),
    "wall.dream_mold": SymbolDef("▚ ", "DM"),
    "wall.silent_stone": SymbolDef("▧▧", "SS"),
    "wall.unconscious_crystal": SymbolDef("◲◲", "UC"),
    "wall.anchor_of_regret": SymbolDef("⌐⌐", "AR"),
    "wall.strata_rock": SymbolDef("❑❑", "SR"),
    "wall.echo_obsidian": SymbolDef("◀◀", "EO"),
    # Excel 新一批（2026-09-18）：石墨烯晶格的六边形晶格感、玉米淀粉墙的软质团块。
    "wall.graphene": SymbolDef("⊞⊞", "GL"),
    "wall.cornstarch": SymbolDef("◇◇", "CS"),
    # ---- 内容扩展包 v1（2026-09-20）----
    "wall.moss_light": SymbolDef("▁▁", "ML"),
    "wall.terracotta": SymbolDef("♜ ", "TC"),
    "wall.mirror_lake": SymbolDef("◍◍", "MK"),
    "wall.cotton_stack": SymbolDef("❅ ", "CT"),
    "wall.copper_mesh": SymbolDef("⌘ ", "CP"),
    "wall.conjured": SymbolDef("▚▚", "FW"),
    "wall.mind_fence": SymbolDef("∩∩", "BF"),
    # 逻辑固体（陷阱/机关石台复用 wall.stone_platform，图标与普通石台一致）。
    "wall.rune_sensor": SymbolDef("⌸ ", "RS"),
    "wall.pendulum": SymbolDef("⌬ ", "PD"),
    "wall.reveal_obelisk": SymbolDef("✧ ", "RO"),
    "wall.cage_post": SymbolDef("⊟ ", "CG"),
    "wall.launcher": SymbolDef("↥ ", "LN"),
    "wall.valve": SymbolDef("⊼ ", "VV"),
    "wall.alarm": SymbolDef("≫ ", "AL"),
    "wall.doorframe": SymbolDef("╪╪", "DC"),
    "wall.rubble": SymbolDef("▚▞", "RB"),
    # ---- 梦中梦·千禧园（M0 探针 26 字形全 SAFE；docs/millennium-garden-design.md §7）----
    "wall.xp_brick": SymbolDef("🧱", "BB"),
    "wall.millennium_tree": SymbolDef("🌳", "MT"),
    "wall.xp_door": SymbolDef("🚪", "DR"),
    "wall.block_red": SymbolDef("🟥", "RR"),
    "wall.block_orange": SymbolDef("🟧", "OO"),
    "wall.block_blue": SymbolDef("🟦", "UU"),
    "wall.block_white": SymbolDef("⬜", "WH"),
    "wall.fax_machine": SymbolDef("📠", "FX"),
    "wall.lightbox": SymbolDef("💡", "LB"),
    "wall.popup": SymbolDef("🪟", "PW"),
    "wall.tape_wall": SymbolDef("📼", "TP"),
    "wall.joystick_post": SymbolDef("🕹 ", "JS"),
    "wall.printer": SymbolDef("🖨 ", "PR"),
    "wall.bsod_terminal": SymbolDef("🖥 ", "BS"),
    "wall.idea_cube": SymbolDef("⊠ ", "IC"),
    "gate.and": SymbolDef("⊗ ", "GA"),
    "gate.or": SymbolDef("⊕ ", "GO"),
    "gate.junction": SymbolDef("✛ ", "GJ"),
    "wall.wood_table": SymbolDef("▤ ", "tb"),
    "wall.stone_platform": SymbolDef("▣ ", "st"),
    "wall.lead": SymbolDef("▛▛", "PB"),
    "wall.salt": SymbolDef("△△", "SC"),
    "wall.boundary": SymbolDef("╬╬", "++"),
    "wall.door": SymbolDef("╫╫", "DD"),
    "liquid.shallow": SymbolDef("∿ ", "~ "),
    "liquid.medium": SymbolDef("≈ ", "~~"),
    "liquid.deep": SymbolDef("≋ ", "=="),
    "gas": SymbolDef("░░", "^^"),
    # 气体浓度三档：按玩家要求恢复地图/图鉴共用的 ░/▒/▓ 点阵纹理；
    # 同一气体三档仍使用同一种气体颜色。
    "gas.faint": SymbolDef("░ ", "gf"),
    "gas.mid": SymbolDef("▒ ", "gm"),
    "gas.high": SymbolDef("▓ ", "gh"),
    "gas.steam": SymbolDef("░ ", "s "),
    "gas.smoke": SymbolDef("▒▒", "sm"),
    "gas.poison": SymbolDef("▓ ", "p "),
    "gas.sedative": SymbolDef("░ ", "a "),
    "gas.alcohol": SymbolDef("▒ ", "w "),
    "gas.obscuring": SymbolDef("▓ ", "o "),
    "gas.flammable": SymbolDef("▒ ", "f "),
    "gas.dust": SymbolDef("░ ", "d "),
    "gas.echo": SymbolDef("▚ ", "e "),
    "gas.scald": SymbolDef("▒ ", "h "),
    "gas.static": SymbolDef("⌁ ", "x "),
    "gas.hypno": SymbolDef("◌ ", "z "),
    # 新气体沿用旧气体的雾符号（░/▒）+ 专属颜色区分（同液体逻辑）。
    "gas.clarity": SymbolDef("░ ", "c "),
    "gas.poppy": SymbolDef("▒ ", "n "),
    "gas.melatonin": SymbolDef("░ ", "m "),
    "gas.caffeine": SymbolDef("▒ ", "k "),
    "gas.spirit": SymbolDef("░ ", "j "),
    "gas.radiation": SymbolDef("▒ ", "r "),
    "gas.whisper": SymbolDef("░ ", "w2"),
    "gas.void_spore": SymbolDef("▒ ", "vs"),
    "gas.dream_acid": SymbolDef("▓ ", "da"),
    "gas.nightmare_breath": SymbolDef("▓ ", "nb"),
    "gas.morning_frost": SymbolDef("░ ", "mf"),
    # 火焰/异象图标不再用 emoji：🔥🥁⏳ 在经典控制台（conhost）经字体
    # 回退常按 1 列渲染而 rich 按 2 列布局，导致行错位。改用窄字符+空格。
    "flame": SymbolDef("▲ ", "!!"),
    "manifestation": SymbolDef("◆ ", "[]"),
    # 可携带的显化物（能装进栏位的物品）**不再一刀切用王冠**：按栏位取专属图标，
    # 见下面的 CARRIED_SLOT_KEYS。carried_image（♕）保留为**未知栏位的回退**
    # 与图鉴「携带意象」分类按钮的图标。
    # 记忆槽不参与栏位映射；记忆专属图标由 item_icons 的效果家族提供。
    "carried_image": SymbolDef("♕ ", "CR"),
    # 栏位专属图标：✎ 手中意象 / ♖ 自我表层 / ⚜︎ 依附物 / ⚒︎ 惯用物。
    # ⚠️ ⚜(U+269C) 与 ⚒(U+2692) 必须带变体选择符 FE0E —— 它们默认可能被字体
    # 按 emoji 呈现：颜色不生效（emoji 不吃前景色）、宽度还可能变 2 列把行挤错位。
    # ✎(U+270E) 与 ♖(U+2656) 本身就是文本字形，四个的 EAW 都是 N/单列，
    # 与既有的 ♕ 同一宽度口径（rich 里各计 1 列，补一个空格正好两列）。
    # 2026-09-18：四种装备的地图/掉落图标改用携带意象页的栏位 emoji
    # （🖋️ 手中意象 / 👕 自我表层 / 🎖️ 依附物 / 🔧 惯用物），统一两处显示。
    # emoji 本身占 2 列，单写即满格、不再双写；ASCII 档沿用三字母码
    # （紧凑地图档不渲染 emoji，走 drop_glyph 的 ascii 回退）。
    "carried_hand": SymbolDef("🖋", "PN"),
    "carried_surface": SymbolDef("👕", "RK"),
    "carried_dependent": SymbolDef("🎖", "FL"),
    "carried_habit": SymbolDef("🔧", "HM"),
    # 异常地点（未回应的事件）：简单事件 ✼ / 复合事件 ❉ 是类别基准；
    # 实际地图用 event_site_glyph 在同类字形池内按事件 ID 稳定分形，
    # 颜色统一保持亮黄——「形状辨种类，颜色标类别」，色盲/低清醒下也读得出。
    "site": SymbolDef("✼ ", "{}"),
    "site_compound": SymbolDef("❉ ", "$$"),
    # 新地板（2026-09-18 Excel）：⨀○●⊘◎⦿ 系符号，与旧地面的「· 」一眼区分。
    "floor.carpet": SymbolDef("❍ ", "CV"),
    "floor.ice": SymbolDef("◌ ", "IC"),
    "floor.star": SymbolDef("✦ ", "SG"),
    "floor.page": SymbolDef("▸ ", "PG"),
    "floor.moon": SymbolDef("☉ ", "MS"),
    "floor.checker": SymbolDef("⊞ ", "CB"),
    "floor.insulation": SymbolDef("◎ ", "TI"),
    "floor.piezo": SymbolDef("◉ ", "PZ"),
    "floor.hollow": SymbolDef("⌀ ", "HD"),
    "floor.pressure": SymbolDef("⊞ ", "PF"),
    # 传送带四向（箭头即指向）
    "floor.belt.n": SymbolDef("↑ ", "^ "),
    "floor.belt.e": SymbolDef("→ ", "> "),
    "floor.belt.s": SymbolDef("↓ ", "v "),
    "floor.belt.w": SymbolDef("← ", "< "),
    # 植物：可穿行的固体地形（不属于墙体，见 Cell.plant）。
    # 发光地衣沿用低草字形、只换颜色（亮黄）；蘑菇用空心草花（♧）与高丛区分。
    "plant.short": SymbolDef("❀ ", "g "),
    "plant.tall": SymbolDef("♣ ", "Y "),
    "plant.lichen": SymbolDef("❀ ", "y "),
    "plant.mushroom": SymbolDef("♧ ", "m "),
    # 无意识领域稀有魔法植物（单株、极稀有）。
    "plant.mandrake": SymbolDef("ψ ", "mr"),
    "plant.datura": SymbolDef("❁ ", "dt"),
    "plant.styx": SymbolDef("ϟ ", "sw"),
    "plant.night_queen": SymbolDef("✾ ", "nq"),
    "plant.soul_vine": SymbolDef("∮ ", "sv"),
    "plant.sage_moss": SymbolDef("⁂ ", "sg"),
    "plant.mirror_orchid": SymbolDef("◈ ", "mo"),
    "plant.lily": SymbolDef("♪ ", "ll"),
    # 浅层/幻觉区域稀有植物（2026-09-18）。
    "plant.mint": SymbolDef("❃ ", "mn"),
    "plant.amber_fern": SymbolDef("✤ ", "af"),
    "plant.daisy": SymbolDef("❋ ", "dy"),
    "plant.glass_shroom": SymbolDef("✱ ", "gs"),
    "plant.whisper_fern": SymbolDef("✾ ", "wf"),
    # 梦中梦/扩展包 v1 新植物（2026-09-21 补注册——漏注册会渲染成 ??）
    "plant.dream_grass": SymbolDef("❂ ", "dg"),
    "plant.thorn_vine": SymbolDef("✽ ", "tv"),
    "plant.vane_moss": SymbolDef("⌖ ", "vm"),
    "plant.wax_bloom": SymbolDef("❊ ", "wb"),
    # 月光蕈/空鼓菌起于「蘑菇换色变体」，本轮各自长出不同机制（减声／巨响），
    # 按设计文档 §4「形状相同、机制不同的两株不能只靠颜色区分」不再共用 ♧：
    # 月光蕈取月牙 ☾，空鼓菌取空心菌盖 ◒。
    "plant.moon_shroom": SymbolDef("☾ ", "mw "),
    "plant.hollow_shroom": SymbolDef("◒ ", "ho2"),
    # ---- 梦中梦·千禧园专属植物（码 24/25）----
    "plant.millennium_grass": SymbolDef("❋ ", "mG "),
    "plant.bubble_algae": SymbolDef("° ", "bA "),
    # 踩倒之后是另一株（H1）：字形压平、ascii 换小写，不能沿用挺立态。
    "plant.millennium_grass_low": SymbolDef("☘ ", "mg "),
    # ---- 三位面专属新增植物（2026-10-26，码 27–41）----
    # 千禧园：电子媒介与软塑料。同一组内不复用主题字。
    "plant.millennium.tape_tangle": SymbolDef("≋ ", "mt"),
    "plant.millennium.dial_reed": SymbolDef("♬ ", "ds"),
    "plant.millennium.contact_whisker": SymbolDef("⌁ ", "cw"),
    "plant.millennium.frame_shard": SymbolDef("▥ ", "fs"),
    # ⌇ 在 Noto 里是极细的竖线（地图轮廓短轴只有整格的 0.21，撑不满一格），
    # 且与「全声合唱」异象同形；热熔须改取实心四瓣火花 ❈。
    "plant.millennium.heat_filament": SymbolDef("❈ ", "hf"),
    # 藏书宫：页 / 线 / 墨 / 留白 / 磨页。
    "plant.library.page_ridge": SymbolDef("▤ ", "pg"),
    "plant.library.binding_tangle": SymbolDef("⋈ ", "bt"),
    "plant.library.ink_wick": SymbolDef("▱ ", "iw"),
    "plant.library.blank_felt": SymbolDef("□ ", "bf"),
    "plant.library.abrasion_tabs": SymbolDef("▨ ", "at"),
    # 至白疗所：缝线 / 滤材 / 光阑 / 压差 / 滴注。
    "plant.hospital.suture_tangle": SymbolDef("⌘ ", "su"),
    "plant.hospital.filter_tuft": SymbolDef("▦ ", "ft"),
    "plant.hospital.shutter_fold": SymbolDef("◧ ", "sf"),
    "plant.hospital.pressure_sac": SymbolDef("◔ ", "px"),
    "plant.hospital.infusion_ampoule": SymbolDef("◖ ", "if"),
    # ---- H1 形态（催生目标，docs §10.1）：同一个东西收着放，字形要能看出
    # 「还没立起来」——平片 / 合页，与立起态的 ▥ ▤ 成对，不另起一套花叶模板。
    "plant.millennium.frame_shard_flat": SymbolDef("▭ ", "fh"),
    "plant.library.page_ridge_flat": SymbolDef("▬ ", "pl"),
    # ---- 耗尽／空壳两档（§4）：一次性对象没有「半」档，只有满与空 ----
    "plant.millennium.tape_tangle.spent": SymbolDef("∿ ", "mt2"),
    "plant.millennium.dial_reed.spent": SymbolDef("♩ ", "ds2"),
    "plant.millennium.contact_whisker.spent": SymbolDef("⌐ ", "cw2"),
    "plant.millennium.frame_shard.spent": SymbolDef("⌷ ", "fs2"),
    "plant.millennium.heat_filament.spent": SymbolDef("∘ ", "hf2"),
    "plant.library.page_ridge.spent": SymbolDef("⌸ ", "pg2"),
    "plant.library.binding_tangle.spent": SymbolDef("⌸ ", "bt2"),
    "plant.library.ink_wick.spent": SymbolDef("▪ ", "iw2"),
    "plant.library.blank_felt.spent": SymbolDef("▫ ", "bf2"),
    "plant.library.abrasion_tabs.spent": SymbolDef("⌙ ", "at2"),
    "plant.hospital.suture_tangle.spent": SymbolDef("⌗ ", "su2"),
    "plant.hospital.filter_tuft.spent": SymbolDef("⊞ ", "ft2"),
    "plant.hospital.shutter_fold.spent": SymbolDef("◨ ", "sf2"),
    "plant.hospital.pressure_sac.spent": SymbolDef("◌ ", "px2"),
    "plant.hospital.infusion_ampoule.spent": SymbolDef("○ ", "if2"),
    "plant.hollow_shroom.spent": SymbolDef("♢ ", "ho3"),
    "plant.mushroom.spent": SymbolDef("♤ ", "m3"),
    "plant.sage_moss.spent": SymbolDef("※ ", "sg2"),
    "plant.vane_moss.spent": SymbolDef("⌗ ", "vm2"),
    "consciousness": SymbolDef("◉ ", "C "),
    "anomaly.page_hound": SymbolDef("𓃡 ", "P "),
    # ---- 梦中梦·千禧园（emoji 异象；M0 探针全 SAFE）----
    "anomaly.bsod_warden": SymbolDef("💀", "BW"),
    "anomaly.rewind_ghost": SymbolDef("⏪", "RG"),
    "anomaly.pager_sprite": SymbolDef("📟", "PS"),
    "anomaly.disco_echo": SymbolDef("🪩", "DE"),
    "anomaly.static_viewer": SymbolDef("📺", "SV"),
    "anomaly.floppy_collector": SymbolDef("💾", "FC"),
    "anomaly.screensaver_bubble": SymbolDef("🫧", "SB"),
    "anomaly.cursor_hunter": SymbolDef("🖱 ", "CH"),
    "anomaly.startup_chorus": SymbolDef("🔊", "SU"),
    "anomaly.deadlink_roamer": SymbolDef("🌐", "DR2"),
    "anomaly.popup_peddler": SymbolDef("🎁", "PU"),
    "anomaly.core_y2k_worm": SymbolDef("🐛", "Y2"),
    "anomaly.folded_person": SymbolDef("𓀠 ", "F "),
    "anomaly.reverse_drummer": SymbolDef("◎ ", "D "),
    "anomaly.model_porter": SymbolDef("𓀃 ", "M "),
    "anomaly.silent_audience": SymbolDef("♙ ", "V "),
    "anomaly.cooling_doll": SymbolDef("♟ ", "C "),
    "anomaly.backlit_reader": SymbolDef("☻ ", "R "),
    "anomaly.echo_door": SymbolDef("⋂ ", "G "),
    "anomaly.faceless_editor": SymbolDef("✍ ", "E "),
    "anomaly.folded_room": SymbolDef("⚚ ", "T "),
    "anomaly.unfinished_period": SymbolDef("@ ", "X "),
    "anomaly.clock_keeper": SymbolDef("⧗ ", "K "),
    "anomaly.mirror_attendant": SymbolDef("⧉ ", "A "),
    "anomaly.paper_fish": SymbolDef("𓆟 ", "B "),
    # ✂︎ 带变体选择符 FE0E 强制文本呈现，避免被渲染成 emoji 导致宽度错位。
    "anomaly.sleepwalking_tailor": SymbolDef("\u2702 ", "L "),
    "anomaly.human_coat_rack": SymbolDef("☂ ", "U "),
    "anomaly.stair_echo": SymbolDef("⌂ ", "H "),
    "anomaly.double_exposure": SymbolDef("❖ ", "2 "),
    "anomaly.wet_choir": SymbolDef("♬ ", "Q "),
    "anomaly.moving_staircase": SymbolDef("⌗ ", "N "),
    "anomaly.hollow_lighthouse": SymbolDef("☼ ", "0 "),
    # ---- 无意识领域（21–27）----
    "anomaly.sunken_bell": SymbolDef("◕ ", "cb"),
    "anomaly.silent_mirror": SymbolDef("⇧ ", "si"),
    "anomaly.thought_worm": SymbolDef("𓆗 ", "tw"),
    "anomaly.faceless_watchman": SymbolDef("☃ ", "fw"),
    "anomaly.nightmare_weaver": SymbolDef("❥ ", "nw"),
    "anomaly.forgetter": SymbolDef("࿐ ", "fg"),
    "anomaly.blank_rift": SymbolDef("□ ", "br"),
    "anomaly.primordial_impulse": SymbolDef("↯ ", "pi"),
    "anomaly.first_cry": SymbolDef("ω ", "fc"),
    # ---- 深层边界（28–30）与内容扩展包异象（2026-09-21 补注册）——
    # 漏注册的后果不是「没有图标」，而是 symbol() 返回 "??"，地图退回 entity.glyph
    # （定义表里的单列字），在两列一格的排版里把整行挤错位。
    "anomaly.scribe": SymbolDef("✒ ", "sc"),
    "anomaly.dream_accountant": SymbolDef("🮔 ", "da"),
    # 2026-09-22：原 ✒ 与执笔者撞字形（定义表已同步改 ☰）。
    "anomaly.ink_archivist": SymbolDef("▤ ", "ia"),
    # 异象技能 v3 新增（2026-09-22）
    "anomaly.pyre_singer": SymbolDef("♨ ", "ps"),
    "anomaly.unopened_gift": SymbolDef("✿ ", "ug"),
    "anomaly.fog_breather": SymbolDef("≋ ", "fb"),
    "anomaly.whole_choir": SymbolDef("⌇ ", "wc"),
    "anomaly.null_witness": SymbolDef("ø ", "zw"),
    # 梦中梦·门之回廊
    "anomaly.door_warden": SymbolDef("⌸ ", "dw"),
    "anomaly.door_mimic": SymbolDef("╫ ", "dm"),
    # 内容扩展包 v2
    "anomaly.ticket_inspector": SymbolDef("𓀅 ", "ti"),
    "anomaly.insomniac_alarm": SymbolDef("✇ ", "al"),
    "anomaly.potted_keeper": SymbolDef("𓆰 ", "pk"),
    "anomaly.subtitle_group": SymbolDef("₩ ", "sg"),
    "anomaly.echo_scribe": SymbolDef("✐ ", "es"),
    "anomaly.slow_projector": SymbolDef("𓊝 ", "sj"),
    "anomaly.return_runner": SymbolDef("𓍯 ", "rr"),
    "anomaly.oblivion_archivist": SymbolDef("𓎛 ", "oa"),
    "anomaly.nightmare_herder": SymbolDef("𓃭 ", "nh"),
    "anomaly.sleepless_watch": SymbolDef("𓀭 ", "sw"),
    "anomaly.ink_bottle_guard": SymbolDef("⚘ ", "ib"),
    "anomaly.lullaby_hummer": SymbolDef("𓅜 ", "lh"),
    "anomaly.projection_crew": SymbolDef("𓊵 ", "pc"),
    "anomaly.long_take_director": SymbolDef("𓎡 ", "ld"),
    "anomaly.silent_proofreader": SymbolDef("𓏲 ", "pr"),
    "anomaly.abyss_ruler": SymbolDef("𓌳 ", "ar"),
    "locked": SymbolDef("？", "??"),
    # 观察模式的光标：白色 ?（「可操作对象」从 ❤ 换成它）。
    "observer": SymbolDef("? ", "? "),
    "cursor": SymbolDef("▸ ", "> "),
    "category_consciousness": SymbolDef("◉ ", "C "),
    "category_manifestation": SymbolDef("◆ ", "I "),
    # 图鉴里「携带意象」是独立分类：分类按钮与条目都用 ♕。
    "category_carried_image": SymbolDef("♕ ", "CC"),
    "category_site": SymbolDef("◇ ", "S "),
    "category_polymer": SymbolDef("▤ ", "8 "),
    "category_liquid_memory": SymbolDef("≈ ", "3 "),
    "category_diffuse_impression": SymbolDef("░ ", "5 "),
    # 「环境反应」分类图标此前漏登记（分类页按钮渲染成 ??，2026-10-11 补）。
    "category_reaction": SymbolDef("◍ ", "R "),
    # 「梦中人」分类（NPC 图鉴，2026-10-11）+ NPC 条目 ascii 档通用回退键。
    # ascii 用 DF（Dream Folk）：'N ' 已被 moving_staircase 占用（ascii 全表唯一性测试）。
    "category_npc": SymbolDef("◯ ", "DF"),
    # 设置页五个分类的页签图标（2026-10-24 玩家要求「设置的标签也在前面加入图标」）。
    # 字形守则照旧：恰好两列（窄字形双写或加空格）、ascii 缩写全表唯一。
    "settings_general": SymbolDef("⚙ ", "GE"),
    "settings_display": SymbolDef("▭▭", "DS"),
    "settings_audio": SymbolDef("♪♪", "AU"),
    "settings_keys": SymbolDef("⏎⏎", "KB"),
    "settings_data": SymbolDef("⎔⎔", "DT"),
    "npc": SymbolDef("† ", "nf"),
    "previous": SymbolDef("◀ ", "< "),
    "next": SymbolDef("▶ ", "> "),
    # ---- 少字模式（terse mode）专用字段图标 ----
    # 状态条：心智 / 清醒 / 想象 / 噪音 / 混乱。语义字体可用时优先语义图标
    # （data/semantic_icons 的 stat.* / noise.pulse）；这里是普通终端回退。
    "stat.mind": SymbolDef("☻ ", "MD"),
    "stat.lucidity": SymbolDef("◉ ", "LC"),
    "stat.imagination": SymbolDef("✦ ", "IM"),
    "stat.noise": SymbolDef("♪ ", "NS"),
    "stat.chaos": SymbolDef("✳ ", "CH"),
    # 右栏子页签（六个工作区下方的各子界面）。
    "section.constructs": SymbolDef("✦ ", "AC"),
    "section.fire": SymbolDef("▲ ", "FR"),
    "section.tamper": SymbolDef("✎ ", "TM"),
    "section.board": SymbolDef("▦ ", "BD"),
    "section.memory": SymbolDef("◈ ", "MM"),
    "section.insights": SymbolDef("◆ ", "IN"),
    "section.portents": SymbolDef("◇ ", "PT"),
    "section.stats": SymbolDef("∑ ", "ST"),
    "section.audit": SymbolDef("⊙ ", "AU"),
    "section.nearby": SymbolDef("◎ ", "NB"),
    "section.records": SymbolDef("▤ ", "RC"),
    "section.quests": SymbolDef("✓ ", "QS"),
    # 面板内部小页签（行囊分类等）：少字模式只显示这些符号。
    "subtab.all": SymbolDef("≣ ", "TA"),
    "subtab.carried": SymbolDef("♕ ", "TC"),
    "subtab.ingest": SymbolDef("♨ ", "TI"),
    "subtab.perishable": SymbolDef("◷ ", "TP"),
    "subtab.interactive": SymbolDef("◇ ", "TX"),
    "subtab.habit": SymbolDef("▣ ", "TH"),
    "subtab.board": SymbolDef("▦ ", "TB"),
    "subtab.memory": SymbolDef("◈ ", "TM"),
    # 右栏工具栏。
    "tool.search": SymbolDef("⌕ ", "SR"),
    "tool.filter": SymbolDef("▽ ", "FL"),
    "tool.sort": SymbolDef("↕ ", "SO"),
    "tool.expand": SymbolDef("+ ", "EX"),
    "tool.menu": SymbolDef("≡ ", "MN"),
    "tool.clear": SymbolDef("× ", "XX"),
    "tool.pin": SymbolDef("⚲ ", "PN"),
    "tool.back": SymbolDef("← ", "BK"),
    "tool.related": SymbolDef("◇ ", "RL"),
    "tool.fold": SymbolDef("≣ ", "FD"),
}


# themed 字形 → ASCII 首字符（地图缩小态的 1 列窄符号）。
NARROW_BY_GLYPH: dict[str, str] = {
    definition.themed: definition.ascii[:1] for definition in SYMBOLS.values()
}

# 栏位 → 图标 key。判据只有 ``Item.slot``（与 category 名解耦）：同一件物品
# 只要换了栏位，地图/行囊/悬停/图鉴四处的图标就会一起跟着换。
# 记忆槽故意缺席：专属家族在物品 registry，未知记忆才使用通用回退。
CARRIED_SLOT_KEYS: dict[str, str] = {
    "手中意象": "carried_hand",
    "自我表层": "carried_surface",
    "依附物": "carried_dependent",
    # 依附物有两个栏位，共用同一个图标。
    "依附物·一": "carried_dependent",
    "依附物·二": "carried_dependent",
    "惯用物": "carried_habit",
}


def carried_slot_key(slot: str | None) -> str:
    """带槽物品的通用字形 key：按栏位取专属图标，空栏位/未知栏位回退到王冠。

    空串与 ``None`` 都走回退——调用方（如图鉴）手上可能只有定义字典的取值，
    没有 Item 对象。
    """
    return CARRIED_SLOT_KEYS.get(str(slot or ""), "carried_image")


CONTINUOUS_WALL_KEYS = frozenset({"solid", "wall.compacted", "wall.hardened", "wall.dense"})


def symbol(key: str, mode: str, unicode_supported: bool = True) -> str:
    definition = SYMBOLS.get(key)
    if definition is None:
        return "??"
    if mode == "themed" and unicode_supported:
        # Restore the original narrow door bars in the reserved two-cell slot.
        if key == 'wall.door':
            return spaced_icon(definition.themed)
        private = themed_icon(key)
        if private is not None:
            return private
        if key in CONTINUOUS_WALL_KEYS:
            return definition.themed
        return spaced_icon(definition.themed)
    return definition.ascii


def map_symbol(key: str, mode: str, unicode_supported: bool = True) -> str:
    """地图格专用取字形入口：优先地图大轮廓图标，其余照旧走 symbol()。

    2026-10-18（docs/261018方案合集.md 第 7 节）：地图两列一格里的墙、特殊地板、
    异象原本取自阅读字体的小轮廓（约占格子 40%），在终端里看起来只是格子中央的
    小标记。map_symbol 只在地图渲染使用；同一语义键在行内、右栏、图鉴仍走
    symbol 的小字形，避免放大版图标挤坏正文排版（§7.5.B 分隔路由）。
    """
    if mode == "themed" and unicode_supported:
        private = themed_map_icon(key)
        if private is not None:
            return private
    return symbol(key, mode, unicode_supported)


def spaced_icon(text: str) -> str:
    """重复大图标只绘一个，保留两列图标槽供字体回退与相邻文字间距。"""
    raw = text.strip()
    if len(raw) == 2 and raw[0] == raw[1]:
        return set_cell_size(raw[0], 2)
    return text


def entity_glyph(glyph: str, mode: str = "themed") -> str:
    """实体自带字形（定义表 glyph / 残影复制来的字形）→ 恰好两列的展示形态。

    地图每格、图鉴每行都按两列排版，而定义表里存的是单列字——不补齐就把整行
    挤错位。历史 bug 正出在这里：23 个异象漏注册 + NPC/残影直接拿单列字形用，
    「异象图标显示错误」的观感大多由此而来。
    """
    text = str(glyph or "").replace('\ufe0e', '').replace('\ufe0f', '').strip()
    # Old saves may still carry selectors from the four now single-codepoint icons.
    if text in ('🕹️','🖨️','🖥️','🖱️'):
        text=text[0]
    if mode != "themed" or not text:
        return "? "
    return set_cell_size(spaced_icon(text), 2)


def glyph_for(icon: str, fallback: str, mode: str, unicode_supported: bool = True) -> str:
    """图标优先的取字形入口：``icon`` 非空就用它，否则回退到 ``fallback`` 查符号表。

    图标一律归一化为**恰好两列**——地图每格、面板与图鉴每行的图标列都按两列
    排版：emoji（📚/📜）本身就是两列宽，不再补空格；窄字符补一个空格填满。
    ASCII 档位或不支持 Unicode 的终端直接回退，避免字体回退把整行搞错位。
    """
    icon = str(icon or "").replace('\ufe0e', '').replace('\ufe0f', '')
    if (icon.startswith(('item.', 'expansion.')) and icon in ICONS):
        definition = ICONS[icon]
        if mode == 'themed' and unicode_supported:
            return themed_icon(icon) or set_cell_size(definition['fallback'], 2)
        if definition.get('ascii_fallback'):
            return definition['ascii_fallback']
        return symbol(fallback, 'ascii', False)
    if mode == 'themed' and unicode_supported and icon.strip() in ('🖋', '👕', '🎖', '🔧', '✎', '♖', '⚜', '⚒'):
        private = themed_icon(fallback)
        if private is not None and fallback.startswith('carried_'):
            return private
    if icon and mode == "themed" and unicode_supported:
        padded = set_cell_size(spaced_icon(icon), 2)
        if padded.strip():
            return padded
    return symbol(fallback, mode, unicode_supported)


_EVENT_SITE_SIMPLE = ("✼ ", "✧ ", "✺ ", "✶ ", "⁂ ")
_EVENT_SITE_COMPOUND = ("❉ ", "❂ ", "❃ ", "✾ ", "✹ ")


def event_site_glyph(event: Any, mode: str = "themed") -> str:
    """异常地点图标：按事件登记的主题字形显示，同一家族允许复用。

    颜色仍统一亮黄（类别）；形状按事件 ID 区分。未登记的新事件退回
    简单/复合两组基础字形，保证不会出现宽度或空白异常。
    """
    from .data.event_icons import event_icon

    compound = str(getattr(event, "kind", "simple") or "simple") == "compound"
    key = str(getattr(event, "catalog_id", "") or getattr(event, "event_id", ""))
    glyph, ascii_fallback = event_icon(key, compound)
    if mode != "themed":
        return ascii_fallback
    return set_cell_size(glyph, 2)


def drop_glyph(
    item: Any, mode: str, unicode_supported: bool = True, *, compact: bool = False
) -> str:
    """掉落物的显示图标：物品定义里写了 ``icon`` 就用它（如书卷 📚、残页 📜），
    否则按**栏位**取专属图标（✎/♖/⚜︎/⚒︎），无槽的掉落物用 ◆。

    这是地图、行囊、悬停三处唯一的取图标入口——判据只有 ``item.slot`` 与
    ``item.icon``，改定义即全局生效，不会出现「地图换了、列表没换」。

    ``compact`` 供**紧凑地图档**（每格只占一列）使用：emoji 是两列宽，塞进一列
    会被裁成空白或溢出错位，因此该档位直接回退 ASCII 字形，交给
    ``glyphs.compact_tile_glyph`` 取首个可见字符。
    """
    slot = getattr(item, "slot", None)
    fallback = carried_slot_key(slot) if slot else "manifestation"
    if compact:
        icon = str(getattr(item, "icon", "") or "").replace('\ufe0e', '').replace('\ufe0f', '')
        if icon in ICONS and ICONS[icon].get('ascii_fallback'):
            return ICONS[icon]['ascii_fallback']
        return symbol(fallback, "ascii")
    return glyph_for(getattr(item, "icon", ""), fallback, mode, unicode_supported)

SYMBOLS.update({
 'wall.library.outer': SymbolDef('▇▇', 'OW'),
 'wall.library.inner': SymbolDef('▙▙', 'IW'),
 'wall.library.glass': SymbolDef('⌒⌒', 'GW'),
 'gas.library.paper_dust': SymbolDef('⠿ ', 'PD'),
 'gas.library.ink_mist': SymbolDef('≈ ', 'IM'),
 'wall.library.shelf': SymbolDef('▤▤', 'SH'),
 'wall.library.cart': SymbolDef('▰▰', 'BC'),
 'wall.library.pillar': SymbolDef('▮▮', 'PL'),
 'wall.library.lamp': SymbolDef('ΩΩ', 'LP'),
})

# 异常地点逐事件字形：地图、图鉴、悬停/详情共用同一登记表。
from .data.event_icons import EVENT_ICONS as _EVENT_ICONS
for _event_id, (_event_glyph, _event_ascii) in _EVENT_ICONS.items():
    SYMBOLS[_event_id] = SymbolDef(_event_glyph, _event_ascii)

from .data.library import LIBRARY_ANOMALIES
from .data.hospital import HOSPITAL_ANOMALIES
from .data.tamper_anomalies import OMISSION_ANOMALY_ID, TAMPER_ANOMALIES
SYMBOLS[OMISSION_ANOMALY_ID] = SymbolDef(TAMPER_ANOMALIES[OMISSION_ANOMALY_ID]['glyph'], 'OM')
# 混乱极高专属异象：👿 🖤 😇 是单码位 emoji（终端两列宽，entity_glyph
# 的 2 列归一化对它们是无操作）；ASCII 档位给两位字母回退。
from .data.chaos_anomalies import CHAOS_ANOMALIES, CHAOS_ANOMALY_IDS
_CHAOS_ASCII = {
    "chaos.wrath": "WR", "chaos.hollow": "HW", "chaos.false_light": "FL",
}
for _catalog in CHAOS_ANOMALY_IDS:
    SYMBOLS[_catalog] = SymbolDef(
        set_cell_size(CHAOS_ANOMALIES[_catalog]['glyph'], 2),
        _CHAOS_ASCII.get(_catalog, '??'))
for _catalog, _definition in {**LIBRARY_ANOMALIES, **HOSPITAL_ANOMALIES}.items():
    # Preserve the literal script identity in both presentation modes.
    SYMBOLS[_catalog] = SymbolDef(set_cell_size(_definition['glyph'], 2), 'Q:' if _catalog == 'library.reader' else set_cell_size(_definition['glyph'], 2))
