# -*- coding: utf-8 -*-
"""构建 Dream Strata Serif Mono：跨平台统一的等宽衬线中文终端字体。

合成管线（全部素材 SIL OFL，可随游戏再分发）：
  底衬    NotoSerifSC-Regular.ttf   Google Fonts 全量 TTF 构建（思源宋体 SC）
  拉丁    VictorMono-Regular.ttf    衬线等宽西文（ASCII/拉丁扩展/框线/方块/盲文）
  符号    NotoSansSymbols{,2}-Regular.ttf、NotoSansMath-Regular.ttf
          补齐思源宋体不覆盖的杂项符号/装饰符/Dingbats（♕♟☰⚜✍…）
  补字    NotoEmoji-Regular.ttf（单色轮廓、OFL-1.1）
          仅按 EXTRA_CPS 白名单补 emoji（2026-10-22：🛢 U+1F6E2）

度量规则（终端按 '0' 的 advance 定义 cell 宽，UPM=1000）：
  EAW W/F -> advance 1000（两格）；其余（含 A/N/Na）-> 500（一格）；
  单格字形墨迹超出 480 时横向等比压缩并重居中（全角字形不动墨迹）。

产物：assets/fonts/DreamStrataSerifMono-Regular.ttf
素材放置于 scripts/_fontsrc/（缺失时自动从国内镜像下载）。
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._c_m_a_p import cmap_format_4, cmap_format_12

HALF, FULL, UPM = 500, 1000, 1000
INK_LIMIT_RATIO = 0.96
READING_ASCENT, READING_DESCENT = 900, -280
FONT_FAMILY = "Dream Strata Serif Mono"
FONT_PSDATA = "DreamStrataSerifMono-Regular"

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR_DEFAULT = ROOT / "scripts" / "_fontsrc"
OUT_DEFAULT = ROOT / "assets" / "fonts" / "DreamStrataSerifMono-Regular.ttf"


def _gf_url(family_css: str) -> str:
    """Google Fonts css2 在非浏览器 UA 下返回单一全量 TTF。"""
    url = f"https://fonts.googleapis.cn/css2?family={family_css}&display=swap"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        css = r.read().decode("utf-8")
    return re.findall(r"https://[^)]+\.ttf", css)[0]


def _sources() -> dict[str, list[str]]:
    return {
        "base": [_gf_url("Noto+Serif+SC:wght@400")],
        "victor": [_gf_url("Victor+Mono")],
        "symbols": ["https://gh-proxy.com/https://github.com/notofonts/notofonts.github.io/raw/main/fonts/NotoSansSymbols/full/ttf/NotoSansSymbols-Regular.ttf"],
        "symbols2": ["https://gh-proxy.com/https://github.com/notofonts/notofonts.github.io/raw/main/fonts/NotoSansSymbols2/full/ttf/NotoSansSymbols2-Regular.ttf"],
        "math": ["https://gh-proxy.com/https://github.com/notofonts/notofonts.github.io/raw/main/fonts/NotoSansMath/full/ttf/NotoSansMath-Regular.ttf"],
        # 冷门脚本补源：仅按 EXOTIC_CPS 白名单取字形，不整表合并。
        "greek": [_gf_url("Noto+Serif:wght@400")],
        "hebrew": [_gf_url("Noto+Serif+Hebrew:wght@400")],
        "georgian": [_gf_url("Noto+Serif+Georgian:wght@400")],
        "tibetan": [_gf_url("Noto+Serif+Tibetan:wght@400")],
        "egyptian": [_gf_url("Noto+Sans+Egyptian+Hieroglyphs")],
        "hangul": [_gf_url("Noto+Serif+KR:wght@400")],
        # 单色 emoji 补源：只按 EXTRA_CPS 取单个字形，不整表合并。
        # 本地 scripts/_fontsrc/notoemoji.ttf 已随构建素材存在，正常构建不联网；
        # 缺失时从 Google Fonts 取同名可变字体（默认 400 字重）作可复现来源。
        "notoemoji": [_gf_url("Noto+Emoji")],
    }


# 白名单码位 -> 来源优先级（异象/NPC 地图字形里的冷门脚本）
EXOTIC_CPS: dict[int, list[str]] = {
    0x03DF: ["greek", "victor"],        # ϟ styx
    0x1D40: ["greek", "victor"],        # ᵀ
    0x05D0: ["hebrew"],                 # א 拒绝誊清者
    0x10E6: ["georgian"],               # ღ 布偶熊
    0x0FD0: ["tibetan"],                # ࿐
    0xAFC8: ["hangul"], 0xBB38: ["hangul"], 0xCC45: ["hangul"],
    **{cp: ["egyptian"] for cp in (
        0x13003, 0x13005, 0x13020, 0x1302D, 0x130E1, 0x130ED, 0x1315C,
        0x13197, 0x1319F, 0x131B0, 0x1329D, 0x132B5, 0x13333, 0x1336F,
        0x1339B, 0x133A1, 0x133F2)},
}


# 2026-10-22：emoji 补字白名单。这些码位在 0x20–0x2FFF 候选区之外，也不属于
# 冷门脚本；只按显式清单并入（不会把 Noto Emoji 其它 1400+ 个 emoji 带进来）。
# 未命中的来源依次回退；reading 模式沿用 _draw_import 的等比 + 垂直适配，
# 不做非等比拉伸。字形统一追加到 glyph 顺序末尾，旧字形 ID 与 glyf 不动。
EXTRA_CPS: dict[int, list[str]] = {
    0x1F6E2: ["notoemoji", "symbols2"],  # 🛢 思绪容器（旧版显示疑似终端 emoji 回退）
}


def fetch_sources(src_dir: Path) -> dict[str, Path]:
    src_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    urls_by_name = None
    for name in _source_names():
        out = src_dir / f"{name}.ttf"
        paths[name] = out
        if out.exists():
            continue
        if urls_by_name is None:
            urls_by_name = _sources()
        for url in urls_by_name[name]:
            try:
                print(f"download {name}: {url[:72]}...")
                urllib.request.urlretrieve(url, out)
                break
            except Exception as err:  # noqa: BLE001
                print(f"  failed: {err}")
        if not out.exists():
            raise SystemExit(f"素材 {name} 下载失败，请手动放置 {out}")
    return paths


def _source_names() -> tuple[str, ...]:
    return ("base", "victor", "symbols", "symbols2", "math",
            "greek", "hebrew", "georgian", "tibetan", "egyptian", "hangul",
            "notoemoji")


def target_advance(cp: int) -> int:
    return FULL if unicodedata.east_asian_width(chr(cp)) in ("W", "F") else HALF


# 这些区间的码位一律重建字形（来源优先级）；区间外保留底衬原字形，
# 只做度量归一。CJK/假名/谚文/全角标点不重建（保宋体墨迹）。
PREFS: list[tuple[int, int, list[str]]] = [
    (0x0020, 0x00FF, ["victor", "base"]),
    (0x0100, 0x017F, ["victor", "base"]),
    (0x2000, 0x20BF, ["victor", "symbols2", "math", "base"]),
    (0x2100, 0x23FF, ["symbols2", "symbols", "math", "victor", "base"]),
    (0x2400, 0x25FF, ["victor", "symbols2", "symbols", "math", "base"]),
    (0x2600, 0x27BF, ["symbols2", "symbols", "math", "base"]),
    (0x27C0, 0x27FF, ["symbols2", "symbols", "math", "base"]),
    (0x2800, 0x2BFF, ["symbols2", "symbols", "math", "base"]),
]


def rebuild_range(cp: int) -> bool:
    return any(lo <= cp <= hi for lo, hi, _ in PREFS)


def prefer_list(cp: int) -> list[str]:
    for lo, hi, names in PREFS:
        if lo <= cp <= hi:
            return names
    return ["base"]


class Store:
    def __init__(self, path: Path):
        self.font = TTFont(path)
        upm = self.font["head"].unitsPerEm
        self.u = UPM / upm
        self.cmap = self.font.getBestCmap()
        self.glyphset = self.font.getGlyphSet()
        self.glyf = self.font["glyf"]

    def bounds(self, gname: str):
        g = self.glyf[gname]
        if g.isComposite():
            return g.getBounds(self.glyphset)
        if g.numberOfContours == 0:
            return None
        return (g.xMin, g.yMin, g.xMax, g.yMax)


def draw_scaled(gs, gname, target, out_pen, u: float = 1.0, *,
                preserve_aspect: bool = False, fit_vertical: bool = False) -> int:
    """按目标宽等比横缩、水平居中地描出源字形（u 做 upm 换算），返回新 xMin。"""
    b = _bounds_of(gs, gname)
    if b is None:
        return 0
    x0, y0, x1, y1 = b
    ink = max(x1 - x0, 1)
    limit_src = (target * INK_LIMIT_RATIO) / u
    sx = 1.0 if ink <= limit_src else limit_src / ink
    sy = sx if preserve_aspect else 1.0
    ty = 0
    if fit_vertical:
        scale = min(1.0, (READING_ASCENT - READING_DESCENT) / max(1, (y1-y0)*sy*u))
        sx *= scale; sy *= scale
        if y1 * sy * u > READING_ASCENT:
            ty = READING_ASCENT - y1 * sy * u
        elif y0 * sy * u < READING_DESCENT:
            ty = READING_DESCENT - y0 * sy * u
    scaled_w = ink * sx * u
    tx = (target - scaled_w) / 2.0 - x0 * sx * u
    # Imported composites refer to glyphs in their source font. Flatten those
    # references before copying, or marks such as middle-dot/approximately vanish.
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    recording = DecomposingRecordingPen(gs)
    gs[gname].draw(recording)
    recording.replay(TransformPen(out_pen, (sx * u, 0, 0, sy * u, tx, ty)))
    return int(round(x0 * sx * u + tx))


def _bounds_of(gs, gname):
    from fontTools.pens.boundsPen import BoundsPen
    pen = BoundsPen(gs)
    try:
        gs[gname].draw(pen)
    except Exception:  # noqa: BLE001
        return None
    return pen.bounds


def reading_graphic(cp: int) -> bool:
    # Terminal-drawn box/block characters deliberately connect across cell edges.
    return not 0x2500 <= cp <= 0x259F and (unicodedata.category(chr(cp)).startswith('S')
                                         or cp in EXOTIC_CPS)


def reading_wide_graphic(cp: int) -> bool:
    # Ordinary arrows and mathematical operators also occur without padding in
    # help text. Only pictographs and the explicit exotic art set may overflow.
    return reading_graphic(cp) and (unicodedata.category(chr(cp)) == 'So'
                                   or cp in EXOTIC_CPS)


def _draw_import(gs, gname, cp, target, pen, u=1.0, *, reading=False):
    graphic = reading and reading_graphic(cp)
    bounds = _bounds_of(gs, gname)
    ink_target = target
    if graphic and reading_wide_graphic(cp) and bounds:
        width, height = bounds[2]-bounds[0], bounds[3]-bounds[1]
        if width*u > target*INK_LIMIT_RATIO and width/max(1, height) >= .9:
            # A following padding space is already reserved by the game's 2-column
            # glyph layout. Keep square art full-size instead of squeezing it thin.
            ink_target = max(target, FULL)
    return draw_scaled(gs, gname, ink_target, pen, u,
                       preserve_aspect=graphic,
                       fit_vertical=reading and not 0x2500 <= cp <= 0x259F)


def build(src_paths: dict[str, Path], out_path: Path, *, reading: bool = False) -> None:
    dest = TTFont(src_paths["base"])
    glyf = dest["glyf"]
    hm = dest["hmtx"].metrics
    vhm = dest["vmtx"].metrics if "vmtx" in dest else None
    cmap: dict[int, str] = dest.getBestCmap()
    stores = {name: Store(p) for name, p in src_paths.items()}

    candidates: set[int] = set()
    for store in stores.values():
        candidates |= set(store.cmap)
    candidates = {cp for cp in candidates if 0x20 <= cp <= 0x2FFF}
    candidates |= set(EXTRA_CPS)  # 白名单 emoji 在 0x20–0x2FFF 之外

    base_order = list(dest.getGlyphOrder())  # 旧字体 glyph 顺序快照，供末尾复位
    replaced = added = 0
    created: set[str] = set()
    creation_order: list[str] = []
    extra_created: list[str] = []
    for cp in sorted(candidates):
        target = target_advance(cp)
        chosen = None
        if cp in EXTRA_CPS:
            preferences = EXTRA_CPS[cp]
        elif reading and 0x20 <= cp < 0x7F:
            preferences = ['base'] + prefer_list(cp)
        else:
            preferences = prefer_list(cp)
        for pref in preferences:
            store = stores[pref]
            if cp in store.cmap:
                chosen = (store, store.cmap[cp])
                break
        if chosen is None:
            continue
        if not (rebuild_range(cp) or cp in EXTRA_CPS):
            continue
        store, gname = chosen
        if store is stores["base"] and cp in cmap:
            continue  # 底衬原字形保留，交给度量归一处理
        new_name = f"g{cp:04X}"
        pen = TTGlyphPen(None)
        lsb = _draw_import(store.glyphset, gname, cp, target, pen, store.u, reading=reading)
        glyf[new_name] = pen.glyph()  # glyf.__setitem__ 自动维护 glyphOrder
        created.add(new_name)
        creation_order.append(new_name)
        if cp in EXTRA_CPS:
            extra_created.append(new_name)
        if cp in cmap:
            replaced += 1
        else:
            added += 1
        cmap[cp] = new_name
        hm[new_name] = (target, lsb)
        if vhm is not None:
            vhm[new_name] = (1000, 0)

    # 冷门脚本白名单：仅补游戏实际用到的异象/NPC 字形。
    for cp, prefs in sorted(EXOTIC_CPS.items()):
        if cp in cmap:
            continue
        for pref in prefs:
            store = stores.get(pref)
            if store is None or cp not in store.cmap:
                continue
            new_name = f"g{cp:05X}"
            pen = TTGlyphPen(None)
            lsb = _draw_import(store.glyphset, store.cmap[cp], cp,
                               target_advance(cp), pen, store.u, reading=reading)
            glyf[new_name] = pen.glyph()
            created.add(new_name)
            creation_order.append(new_name)
            cmap[cp] = new_name
            hm[new_name] = (target_advance(cp), lsb)
            if vhm is not None:
                vhm[new_name] = (1000, 0)
            added += 1
            break

    # 度量归一：候选区 advance 强制 HALF/FULL；单格超宽墨迹压缩。
    # 区外（CJK/假名/全角标点）墨迹与 advance 均保留底衬原状。
    dest_glyphset = dest.getGlyphSet()
    for cp, gname in list(cmap.items()):
        if not (0x20 <= cp <= 0x2FFF):
            continue
        target = target_advance(cp)
        if gname not in created:
            b = None
            g = glyf[gname]
            if g.numberOfContours != 0 or g.isComposite():
                b = _bounds_of(dest_glyphset, gname)
            if b is not None and ((target == HALF and (b[2] - b[0]) > target * INK_LIMIT_RATIO)
                                 or (reading and not 0x2500 <= cp <= 0x259F
                                     and (b[1] < READING_DESCENT or b[3] > READING_ASCENT))):
                pen = TTGlyphPen(None)
                lsb = _draw_import(dest_glyphset, gname, cp, target, pen, reading=reading)
                glyf[gname] = pen.glyph()
                hm[gname] = (target, lsb)
                continue
        hm[gname] = (target, hm.get(gname, (0, 0))[1])

    # EXTRA_CPS 白名单字形统一排到末尾：旧字形 glyph ID / loca 偏移保持不变，
    # 重建后旧 glyf 字节仍是新表的前缀，便于逐项核对"其它码位未变"。
    final_order = base_order + creation_order
    if extra_created:
        extras = set(extra_created)
        final_order = base_order + [name for name in creation_order
                                    if name not in extras] + extra_created
    _install_cmap(dest, cmap)
    dest.setGlyphOrder(final_order)
    dest["head"].recalcBBoxes = True
    dest["post"].isFixedPitch = 1
    _rename(dest)
    if reading:
        for name_id, value in {1: 'Dream Strata Song Reading', 2: 'Regular',
            3: 'DreamStrataSongReading:1.0', 4: 'Dream Strata Song Reading',
            6: 'DreamStrataSongReading-Regular', 16: 'Dream Strata Song Reading', 17: 'Regular'}.items():
            dest['name'].removeNames(nameID=name_id)
            dest['name'].setName(value, name_id, 3, 1, 0x409)
        dest['OS/2'].usWeightClass = 500
        # A compact shared baseline retains Latin descenders and CJK punctuation.
        # Paired with cell_width=1.18, two columns and one row form a square tile.
        dest['hhea'].ascent = dest['OS/2'].sTypoAscender = READING_ASCENT
        dest['hhea'].descent = dest['OS/2'].sTypoDescender = READING_DESCENT
        dest['hhea'].lineGap = dest['OS/2'].sTypoLineGap = 0
        dest['OS/2'].fsSelection |= 1 << 7  # USE_TYPO_METRICS
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dest.save(out_path)
    print(f"saved {out_path} ({out_path.stat().st_size / 1e6:.1f} MB) "
          f"replaced={replaced} added={added} cmap={len(cmap)}")


def _install_cmap(dest: TTFont, mapping: dict[int, str]) -> None:
    bmp = {cp: n for cp, n in mapping.items() if cp <= 0xFFFF}
    table = newTable("cmap")
    table.tableVersion = 0
    subs = []
    for plat, enc, lang, sub, fmt in ((3, 1, 0, bmp, 4), (3, 10, 0, mapping, 12),
                                      (0, 3, 0, bmp, 4), (0, 4, 0, mapping, 12)):
        st = cmap_format_4(fmt) if fmt == 4 else cmap_format_12(fmt)
        st.platformID, st.platEncID, st.language = plat, enc, lang
        st.format = fmt
        st.cmap = dict(sub)
        subs.append(st)
    table.tables = subs
    dest["cmap"] = table


def _rename(dest: TTFont) -> None:
    strings = {
        1: FONT_FAMILY, 2: "Regular", 3: f"{FONT_PSDATA}:1.0",
        4: f"{FONT_FAMILY} Regular", 6: FONT_PSDATA, 5: "Version 1.0",
        7: FONT_FAMILY, 8: "Dream Strata",
        13: "SIL Open Font License 1.1 - see LICENSES.md",
        14: "https://openfontlicense.org",
    }
    for name_id, value in strings.items():
        dest["name"].setName(value, name_id, 3, 1, 0x409)
    dest["OS/2"].fsType = 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-dir", type=Path, default=SRC_DIR_DEFAULT)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    paths = fetch_sources(args.src_dir)
    build(paths, args.out)
