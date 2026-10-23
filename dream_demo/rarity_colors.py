"""稀有度配色：以物品本色为中心的四档亮度微调。

放在顶层中立模块，供 ``ui.styles``（渲染）与 ``catalog_registry``（图鉴）
共用——后者处在数据层，引 ui.styles 会构成循环导入
（ui.app 反向依赖 build_catalog_definitions）。

四档阶梯（差异可辨、不重叠、不刺眼）：
常见 = 本色；少见 = 提亮 14%；稀有 = 提亮 28%；非常稀有 = 压暗 18%。
"""

from __future__ import annotations

_RARITY_STEPS: dict[str, float] = {"常见": 0.0, "少见": 0.14, "稀有": 0.28, "非常稀有": -0.18}


def _to_hex(base_color: str) -> str | None:
    """把 rich/textual 两套色名都解析成 #rrggbb；失败返回 None。"""
    from textual.color import Color
    try:
        return Color.parse(base_color).hex
    except Exception:
        pass
    try:
        # rich 的命名色（bright_yellow 等）textual 不认，转经 rich 取真彩值。
        from rich.color import Color as RichColor
        triplet = RichColor.parse(base_color).get_truecolor()
        return "#{:02x}{:02x}{:02x}".format(triplet.red, triplet.green, triplet.blue)
    except Exception:
        return None


def apply_rarity(base_color: str, rarity: str) -> str:
    """按稀有度把物品本色沿亮度轴微调；未知档位或不可解析时原样返回。"""
    delta = _RARITY_STEPS.get(rarity)
    if not delta:
        return base_color
    hex_color = _to_hex(base_color)
    if hex_color is None:
        return base_color
    from textual.color import Color
    base = Color.parse(hex_color)
    adjusted = base.lighten(delta) if delta > 0 else base.darken(-delta)
    return adjusted.hex


# 同一图标家族内相距足够的色相/明度偏移；index 0 保留本色。
# 只用于「同图标、同底色」的显化物/携带意象，让形状复用不等同于配色重复。
_VARIANT_STEPS: tuple[tuple[float, float, float], ...] = (
    (0.0, 0.0, 0.0),
    (30.0, 0.08, 0.10), (-30.0, -0.06, 0.10),
    (60.0, 0.12, 0.06), (-60.0, -0.10, 0.06),
    (90.0, 0.06, 0.12), (-90.0, -0.08, 0.12),
    (120.0, 0.14, 0.04), (-120.0, -0.12, 0.04),
    (150.0, 0.04, 0.14), (-150.0, -0.04, 0.14),
    (180.0, 0.10, 0.02), (15.0, -0.14, 0.08), (-15.0, 0.02, -0.10),
)

_VARIANT_CACHE: dict[str, str] | None = None


def _variant_color_at(base_color: str, index: int) -> str:
    if index <= 0:
        return base_color
    hex_color = _to_hex(base_color)
    if hex_color is None:
        return base_color
    import colorsys
    red, green, blue = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    hue_delta, light_delta, sat_delta = _VARIANT_STEPS[index % len(_VARIANT_STEPS)]
    h = (hue + hue_delta / 360.0) % 1.0
    l = min(0.92, max(0.12, lightness + light_delta))
    s = min(1.0, max(0.0, saturation + sat_delta))
    if s < 0.25 or l > 0.80:
        # 白色/近白底色仅靠明度差几乎不可辨；给后续成员补足饱和度并拉开明度。
        s = min(0.85, 0.34 + 0.07 * (index % 4))
        l = min(0.88, max(0.38, lightness + light_delta * 1.8))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return '#{:02x}{:02x}{:02x}'.format(round(r * 255), round(g * 255), round(b * 255))


def _build_variant_cache() -> dict[str, str]:
    """按图标家族给每个物品分配最终显示色，组内保证颜色不再完全相同。"""
    from .core.content import ITEM_DEFINITIONS
    from .data.item_icons import item_icon

    groups: dict[str, list[str]] = {}
    for definition_id, definition in ITEM_DEFINITIONS.items():
        icon = item_icon(definition_id, definition)
        if not icon.startswith('item.'):
            # 原有显式图标保留既定颜色，不为它们重新分配配色。
            continue
        groups.setdefault(icon, []).append(definition_id)
    cache: dict[str, str] = {}
    for ids in groups.values():
        used: set[str] = set()
        for wanted, definition_id in enumerate(sorted(ids)):
            definition = ITEM_DEFINITIONS[definition_id]
            base = str(definition.get('color') or 'bright_white')
            if definition.get('rarity'):
                base = apply_rarity(base, str(definition['rarity']))
            color = _variant_color_at(base, wanted)
            step = wanted
            while color in used:  # 不同底色偶尔会撞到同一结果；沿色阶继续找。
                step += 1
                color = _variant_color_at(base, step)
                if step > wanted + 4 * len(_VARIANT_STEPS):
                    color = '#{:02x}{:02x}{:02x}'.format(
                        (0x30 + wanted * 13) % 256,
                        (0x90 + wanted * 29) % 256,
                        (0xd0 + wanted * 47) % 256)
                    break
            used.add(color)
            cache[definition_id] = color
    return cache


def item_variant_color(definition_id: str, base_color: str) -> str:
    """家族图标物品的稳定配色；同家族内每个物品取不同色相/明度偏移。

    最终颜色在缓存里按家族统一分配，调用方传入的底色只用于非家族物品兜底。
    """
    global _VARIANT_CACHE
    if _VARIANT_CACHE is None:
        _VARIANT_CACHE = _build_variant_cache()
    return _VARIANT_CACHE.get(str(definition_id), base_color)
