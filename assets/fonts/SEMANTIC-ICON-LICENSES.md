# Semantic icon subset licenses (2026-10-19)

First batch: 69 glyphs; reserves: 32 (metadata only, not packaged).

| Subset | Upstream | License | License file |
|---|---|---|---|
| Dream Strata Interface Icons | Phosphor Bold | MIT | `LICENSE-Phosphor-MIT.txt` |
| Dream Strata Material Icons | Material Design Icons 7.4.47 | Apache-2.0 | `LICENSE-MDI-Apache-2.0.txt`, `NOTICE-MDI.txt` |
| Dream Strata Dream Icons | Game-icons.net 20200315a | CC BY 3.0 | `LICENSE-GameIcons-CC-BY-3.0.txt`, `ATTRIBUTION-GameIcons.md` |

The subsets contain only the selected remapped outlines, not the upstream
font cmaps, ASCII/CJK or brand glyphs. Original source hashes and per-glyph
provenance are recorded in `semantic-icons.json`.
# Terminal geometry repair (2026-10-31)

The three semantic subsets use the reading font's 900/-280 baseline and a
900-unit square centred at (500, 310). Outlines preserve their aspect ratio
and actual side bearings. These metric changes do not change codepoints,
icon identities, upstream attribution, or licenses. Rebuild with
`scripts/build_semantic_icon_fonts.py`; hashes are in `semantic-icons.json`.

