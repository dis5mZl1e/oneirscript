# -*- coding: utf-8 -*-
"""构建统一单色候选字体：阅读主字体 + 全部已登记 PUA 图标。

为什么不直接合并文件：四份图标字体的 UPM 与阅读字体相同（1000），但字体表、
复合组件和名称空间各自独立。这里逐码位拆解轮廓后按 1:1 复制，保留源前进宽、
源基线位置与源包围盒；任何缩放/平移都会改变 WezTerm 的现有视觉基准。

产物（默认写入 ``assets/fonts``，但**不覆盖** ``DreamStrataSongReading-*``）：

* ``DreamStrataUnified-Regular.ttf`` —— 候选，family ``Dream Strata Unified``；
* ``unified-font.json`` —— 来源哈希、许可、逐码位来源、验证差值。

默认不把候选设为游戏字体；接入与原生验收见 C3/C4。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._c_m_a_p import cmap_format_4, cmap_format_12

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets" / "fonts"
BASE_FILE = "DreamStrataSongReading-Regular.ttf"
OUT_FILE = "DreamStrataUnified-Regular.ttf"
MANIFEST_FILE = "unified-font.json"

FAMILY = "Dream Strata Unified"
PS_NAME = "DreamStrataUnified-Regular"
VERSION = "1.0"

PUA_LO, PUA_HI = 0xE000, 0xF8FF

# 只合并已登记的单色图标字体；千禧园彩色 emoji 继续独立路由。
SOURCES: tuple[dict, ...] = (
    dict(file="DreamStrataIcons.ttf", licence="OFL-1.1",
         upstream="Noto Emoji / Noto Sans Symbols / Noto Sans Math / Noto Serif / Noto Serif SC / Noto Sans Egyptian Hieroglyphs (Google LLC)"),
    dict(file="DreamStrataInterfaceIcons.ttf", licence="MIT", upstream="Phosphor Icons"),
    dict(file="DreamStrataMaterialIcons.ttf", licence="Apache-2.0", upstream="Material Design Icons"),
    dict(file="DreamStrataDreamIcons.ttf", licence="CC-BY-3.0", upstream="GameIcons"),
)

TOLERANCE = 1  # 字体单位；UPM=1000 时约 0.1% em
# head.modified 默认取构建时刻，会让同输入产出不同字节；固定为
# 2026-01-01T00:00:00Z（1904 纪元起算），manifest 哈希才可复现重算。
BUILD_MODIFIED = 3_850_070_400


class FontConflictError(RuntimeError):
    """两个来源声明同一码位，或基础字体现有码位被覆盖。"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bounds(glyph_set, name: str):
    pen = BoundsPen(glyph_set)
    try:
        glyph_set[name].draw(pen)
    except Exception:  # noqa: BLE001 - 缺轮廓按无墨迹处理，由验证报告缺项
        return None
    return pen.bounds


def find_conflicts(cmaps: list[dict[int, str]]) -> list[int]:
    seen: dict[int, int] = {}
    conflicts: set[int] = set()
    for index, cmap in enumerate(cmaps):
        for cp in cmap:
            if cp in seen and seen[cp] != index:
                conflicts.add(cp)
            else:
                seen[cp] = index
    return sorted(conflicts)


def _icon_sources(assets: Path) -> list[tuple[dict, TTFont, dict[int, str]]]:
    loaded = []
    for spec in SOURCES:
        path = assets / spec["file"]
        if not path.is_file():
            raise SystemExit(f"缺少图标字体：{path}")
        font = TTFont(path)
        cmap = {cp: name for cp, name in font.getBestCmap().items()
                if PUA_LO <= cp <= PUA_HI}
        loaded.append((dict(spec, path=path, font=font, sha256=sha256(path),
                            family=font["name"].getDebugName(1), upm=font["head"].unitsPerEm),
                       font, cmap))
    return loaded


def _install_cmap(dest: TTFont, mapping: dict[int, str]) -> None:
    bmp = {cp: name for cp, name in mapping.items() if cp <= 0xFFFF}
    table = newTable("cmap")
    table.tableVersion = 0
    subs = []
    for plat, enc, fmt in ((3, 1, 4), (3, 10, 12), (0, 3, 4), (0, 4, 12)):
        sub = cmap_format_4(fmt) if fmt == 4 else cmap_format_12(fmt)
        sub.platformID, sub.platEncID, sub.language = plat, enc, 0
        sub.format = fmt
        sub.cmap = dict(bmp if fmt == 4 else mapping)
        subs.append(sub)
    table.tables = subs
    dest["cmap"] = table


def _rename(dest: TTFont) -> None:
    names = {1: FAMILY, 2: "Regular", 3: f"{PS_NAME}:{VERSION}",
             4: f"{FAMILY} Regular", 5: f"Version {VERSION}", 6: PS_NAME,
             16: FAMILY, 17: "Regular",
             13: "Merged from OFL-1.1 / MIT / Apache-2.0 / CC-BY-3.0 sources; see LICENSES.md",
             14: "https://openfontlicense.org"}
    for name_id, value in names.items():
        dest["name"].setName(value, name_id, 3, 1, 0x409)


def build(assets: Path, out_path: Path, manifest_path: Path) -> dict:
    base_path = assets / BASE_FILE
    if not base_path.is_file():
        raise SystemExit(f"缺少基础阅读字体：{base_path}")
    base = TTFont(base_path)
    base.recalcTimestamp = False  # 否则 save 会把 head.modified 改回当前时间
    base_family = base["name"].getDebugName(1)
    base_cmap = dict(base.getBestCmap())
    base_pua = sorted(cp for cp in base_cmap if PUA_LO <= cp <= PUA_HI)
    if base_pua:
        raise FontConflictError(f"基础字体已含 PUA 码位：{base_pua[:8]}")
    if base["head"].unitsPerEm != 1000:
        raise SystemExit("基础字体 UPM 不是 1000，现有度量基准不再成立。")

    sources = _icon_sources(assets)
    conflicts = find_conflicts([cmap for _, _, cmap in sources])
    # 基础字体若已占同码位也属于冲突（当前为 0，仍显式检查）。
    conflicts = sorted(set(conflicts) | {cp for _, _, cmap in sources for cp in cmap
                                         if cp in base_cmap})
    if conflicts:
        raise FontConflictError(
            "PUA 码位冲突：" + ", ".join(f"U+{cp:04X}" for cp in conflicts[:12]))

    glyf = base["glyf"]
    hmtx = base["hmtx"].metrics
    vmtx = base["vmtx"].metrics if "vmtx" in base else None
    order = list(base.getGlyphOrder())
    cmap = dict(base_cmap)
    created: list[str] = []
    records: list[dict] = []

    for spec, font, icon_cmap in sources:
        scale = 1000 / spec["upm"]
        glyph_set = font.getGlyphSet()
        source_hmtx = font["hmtx"].metrics
        for cp in sorted(icon_cmap):
            source_name = icon_cmap[cp]
            target_name = f"u{cp:04X}"
            if target_name in order:
                target_name = f"pua{cp:04X}"
            recording = DecomposingRecordingPen(glyph_set)
            glyph_set[source_name].draw(recording)
            pen = TTGlyphPen(None)
            recording.replay(TransformPen(pen, (scale, 0, 0, scale, 0, 0)))
            glyf[target_name] = pen.glyph()
            advance, lsb = source_hmtx[source_name]
            hmtx[target_name] = (round(advance * scale), round(lsb * scale))
            if vmtx is not None:
                vmtx[target_name] = (1000, 0)
            cmap[cp] = target_name
            created.append(target_name)
            records.append(dict(code=cp, source=spec["file"], glyph=source_name,
                                target=target_name, advance=round(advance * scale)))

    final_order = order + created
    base.setGlyphOrder(final_order)
    base["maxp"].numGlyphs = len(final_order)
    base["hhea"].numberOfHMetrics = len(final_order)
    _install_cmap(base, cmap)
    base["OS/2"].usFirstCharIndex = min(cmap)
    base["OS/2"].usLastCharIndex = min(0xFFFF, max(cmap))
    base["head"].recalcBBoxes = True
    base["head"].modified = BUILD_MODIFIED
    _rename(base)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path)

    verification = verify(out_path, sources)
    manifest = {
        "schema": 1,
        "candidate": True,
        "default": False,
        "builder": "scripts/build_unified_game_font.py",
        "family": FAMILY,
        "postscript_name": PS_NAME,
        "version": VERSION,
        "file": out_path.name,
        "sha256": sha256(out_path),
        "size": out_path.stat().st_size,
        "base": {"file": BASE_FILE, "sha256": sha256(base_path),
                 "family": base_family,
                 "units_per_em": 1000,
                 "half_advance": 500, "full_advance": 1000,
                 "ascent": int(base["hhea"].ascent),
                 "descent": int(base["hhea"].descent),
                 "line_gap": int(base["hhea"].lineGap)},
        "sources": [{key: spec[key] for key in
                     ("file", "sha256", "family", "upm", "licence", "upstream")}
                    for spec, _, _ in sources],
        "pua": {"count": len(records),
                "codepoints": [f"U+{row['code']:04X}" for row in records],
                "conflicts": [],
                "per_source": {spec["file"]: sum(1 for row in records
                                                 if row["source"] == spec["file"])
                               for spec, _, _ in sources}},
        "transform": {"scale": 1.0, "translate": [0, 0],
                      "advance": "source", "baseline": "source"},
        "verification": verification,
        "licence_note": "物理合并仅限允许改名的 OFL/MIT/Apache/CC-BY 单色轮廓；"
                        "彩色 emoji 未合并，继续独立路由。",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    return manifest


def verify(out_path: Path, sources) -> dict:
    """重新打开产物，逐码位复核覆盖、前进宽、包围盒与基础度量。"""
    out = TTFont(out_path)
    cmap = out.getBestCmap()
    glyph_set = out.getGlyphSet()
    hmtx = out["hmtx"].metrics
    missing: list[str] = []
    advance_mismatch: list[dict] = []
    bbox_mismatch: list[dict] = []
    for spec, font, icon_cmap in sources:
        scale = 1000 / spec["upm"]
        source_set = font.getGlyphSet()
        source_hmtx = font["hmtx"].metrics
        for cp, source_name in sorted(icon_cmap.items()):
            target = cmap.get(cp)
            if target is None:
                missing.append(f"U+{cp:04X}")
                continue
            delta = abs(hmtx[target][0] - round(source_hmtx[source_name][0] * scale))
            if delta > TOLERANCE:
                advance_mismatch.append({"code": f"U+{cp:04X}", "delta": delta})
            src_bounds = _bounds(source_set, source_name)
            out_bounds = _bounds(glyph_set, target)
            if (src_bounds is None) != (out_bounds is None):
                bbox_mismatch.append({"code": f"U+{cp:04X}", "reason": "outline presence"})
                continue
            if src_bounds is None:
                continue
            scaled = tuple(round(value * scale) for value in src_bounds)
            if any(abs(a - b) > TOLERANCE for a, b in zip(scaled, out_bounds)):
                bbox_mismatch.append({"code": f"U+{cp:04X}",
                                      "source": list(scaled), "output": list(out_bounds)})
    return {"missing": missing,
            "advance_mismatch": advance_mismatch,
            "bbox_mismatch": bbox_mismatch,
            "ok": not (missing or advance_mismatch or bbox_mismatch)}


def check(assets: Path, out_path: Path, manifest_path: Path) -> int:
    """--check：只复核现有产物与清单，不重新生成。"""
    if not out_path.is_file() or not manifest_path.is_file():
        print("候选或清单不存在，先运行构建。", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest_ok = sha256(out_path) == manifest["sha256"]
    sources = _icon_sources(assets)
    report = verify(out_path, sources)
    print(json.dumps({"sha256_matches": digest_ok, **report}, ensure_ascii=False))
    return 0 if digest_ok and report["ok"] else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, default=ASSETS)
    parser.add_argument("--out", type=Path, default=ASSETS / OUT_FILE)
    parser.add_argument("--manifest", type=Path, default=ASSETS / MANIFEST_FILE)
    parser.add_argument("--check", action="store_true", help="只复核现有候选与清单")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.check:
        return check(args.assets, args.out, args.manifest)
    manifest = build(args.assets, args.out, args.manifest)
    print(json.dumps({"ok": manifest["verification"]["ok"],
                      "pua": manifest["pua"]["count"],
                      "size": manifest["size"],
                      "sha256": manifest["sha256"]}, ensure_ascii=False))
    return 0 if manifest["verification"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
