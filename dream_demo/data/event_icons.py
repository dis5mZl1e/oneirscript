"""Per-event anomaly-site glyphs (monochrome text symbols, family reuse allowed).

Every glyph is a single-column text character + one cell of padding so the site
still fills a two-column map cell. Families keep related sites visually close
(stars for celestial/light, notes for sound, wave/technical forms for
water/radio, geometric frames for containers, etc.); repeated glyphs are
intentional within a family.

All characters here are chosen outside the symbols already used by liquids,
gases, walls and other map features, so a site never masquerades as a
different material. ASCII fallbacks are globally unique (see the end of file).
"""

# event id -> (themed glyph, two-character ASCII fallback placeholder;
# placeholders are replaced with globally unique codes below)
EVENT_ICONS: dict[str, tuple[str, str]] = {
    # ---- 声音 / 音乐 ----
    'event.empty_score': ('♩ ', 'MU'),
    'event.fog_organ': ('♫ ', 'MU'),
    'event.wet_score': ('♭ ', 'MU'),
    'event.elevator_music': ('♮ ', 'MU'),
    'event.static_choir': ('♯ ', 'MU'),
    'event.first_echo': ('♩ ', 'MU'),
    'event.midnight_broadcast': ('♫ ', 'MU'),
    'event.vault_rehearsal': ('♭ ', 'MU'),
    # ---- 电台 / 水 / 雨 ----
    'event.radio_rain': ('⌢ ', 'WV'),
    'event.static_radio': ('∾ ', 'WV'),
    'event.rain_upside_down': ('⌣ ', 'WV'),
    'event.rusty_faucet': ('≀ ', 'WV'),
    'event.bath_tide': ('∻ ', 'WV'),
    'event.tide_of_names': ('⌢ ', 'WV'),
    'event.dry_fountain': ('⌣ ', 'WV'),
    'event.swimming_furniture': ('≀ ', 'WV'),
    'event.vault_circuit_log': ('∾ ', 'WV'),
    # ---- 星辰 / 光 / 灯 ----
    'event.paper_moon': ('✵ ', 'ST'),
    'event.model_lamp': ('✸ ', 'ST'),
    'event.ash_lighter': ('✹ ', 'ST'),
    'event.stargazer_desk': ('✻ ', 'ST'),
    'event.star_clearance': ('✵ ', 'ST'),
    'event.lens_exchange': ('✸ ', 'ST'),
    # ---- 时间 / 机械 ----
    'event.gear_afternoon': ('◷ ', 'CK'),
    'event.tide_clock': ('◴ ', 'CK'),
    'event.broken_meter': ('◶ ', 'CK'),
    'event.clock_repairs': ('◵ ', 'CK'),
    'event.vault_return_loop': ('◷ ', 'CK'),
    # ---- 书页 / 记录 ----
    'event.editor_note': ('◪ ', 'BK'),
    'event.silent_library': ('◩ ', 'BK'),
    'event.torn_library': ('◨ ', 'BK'),
    'event.vault_quiet_ward': ('◧ ', 'BK'),
    'event.vault_repair_desk': ('◰ ', 'BK'),
    'event.vault_seed_ledger': ('◱ ', 'BK'),
    # ---- 信件 / 票证 / 路线 ----
    'event.post_to_waking': ('✉︎ ', 'LT'),
    'event.wet_letterbox': ('✉︎ ', 'LT'),
    'event.dream_post_office': ('✉︎ ', 'LT'),
    'event.silent_ticket': ('⚑ ', 'LT'),
    'event.vault_route_board': ('⚐ ', 'LT'),
    'event.tape_line': ('⌹ ', 'LT'),
    # ---- 镜子 / 玻璃 / 影像 ----
    'event.glass_crack': ('◊ ', 'MR'),
    'event.mirror_interview': ('◐ ', 'MR'),
    'event.mirror_rehearsal': ('◑ ', 'MR'),
    'event.polaroid_wall': ('◓ ', 'MR'),
    'event.photo_booth': ('◔ ', 'MR'),
    'event.blank_gallery': ('◖ ', 'MR'),
    'event.last_train_window': ('◗ ', 'MR'),
    # ---- 门 / 房间 / 容器 ----
    'event.attic_staircase': ('⌵ ', 'DR'),
    'event.wardrobe_door': ('⌶ ', 'DR'),
    'event.doors_within': ('⌷ ', 'DR'),
    'event.dream_bottle': ('⌺ ', 'DR'),
    'event.dream_balloon': ('⌵ ', 'DR'),
    'event.coffee_ring': ('⌶ ', 'DR'),
    'event.wax_tea_party': ('⌷ ', 'DR'),
    # ---- 工具 / 零件 / 行李 ----
    'event.missing_screw': ('✙ ', 'TL'),
    'event.toolbox_grave': ('✞ ', 'TL'),
    'event.lost_luggage': ('✜ ', 'TL'),
    'event.scrapper_case': ('✟ ', 'TL'),
    'event.night_stand': ('✚ ', 'TL'),
    # ---- 医疗 / 人物 / 其他 ----
    'event.pill_box': ('✚ ', 'MD'),
    'event.night_ward_round': ('✜ ', 'MD'),
    'event.puppet_rehearsal': ('✞ ', 'PP'),
    'event.sunken_bell': ('✟ ', 'BL'),
    # ---- 珍品机会（22／24／26 层各一次的高成本场合）----
    'treasure.breach': ('❖ ', 'TR'),
    'treasure.storm': ('⟡ ', 'TR'),
    'treasure.dawn': ('❋ ', 'TR'),
}

# 没有登记的事件退回这两组；这两个字形保留为「未知站点」的兜底。
EVENT_SIMPLE_FALLBACK = ('✼ ', '{}')
EVENT_COMPOUND_FALLBACK = ('❉ ', '$$')


def event_icon(event_id: str, compound: bool = True) -> tuple[str, str]:
    icon = EVENT_ICONS.get(str(event_id))
    if icon is not None:
        return icon
    return EVENT_COMPOUND_FALLBACK if compound else EVENT_SIMPLE_FALLBACK


# ASCII 回退码必须全局唯一（紧凑地图/无 Unicode 终端也会彼此区分）；
# E0–Ez 共 62 个，F0–F9 再补 10 个，覆盖当前 66 个事件。
_ASCII_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
_ascii_codes = [f'E{char}' for char in _ASCII_ALPHABET] + [f'F{index}' for index in range(10)]
for _index, _event_id in enumerate(sorted(EVENT_ICONS)):
    _glyph, _old_ascii = EVENT_ICONS[_event_id]
    EVENT_ICONS[_event_id] = (_glyph, _ascii_codes[_index])
