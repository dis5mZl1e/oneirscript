# Oneirscript v0.1.1

Released 2026-11-01. Desktop packages are available for Windows x64, Linux x64,
macOS Apple Silicon and macOS Intel. Choose **`-en`** for English or **`-zh`** for
Chinese, then extract the whole archive.

## What's new in 0.1.1

- **First-dream introduction.** A six-step welcome explains movement, descent and
  ascent, equipment sentences, tampering and combat; it can be paged or dismissed
  without spending a turn, and can be reopened from Settings → Data.
- **Inventory and build screens.** Five-per-row inventory grid with rarity framing,
  larger item icons, quantity overlays, item details above the grid, category-tinted
  Conception cards, and a switchable grid/column layout.
- **Map, glyphs and depth cues.** PUA glyph style is now the default; plants,
  materials and object glyphs were redrawn; gases show three density bands, liquids
  use their own glyphs, and the map gains zoom/full-map controls.
- **Controls and tamper editor.** The in-game key table was rewritten (equipment
  board, tamper editor, home/save slots, inventory rows, context keys), and the
  tamper panel gained a readable guide plus confirm/cancel entries.
- **Firing and reloading.** Firing sources are shown as cards with magazine counts,
  manual reload entry, remembered source choice and automatic fallback when a
  consumable is exhausted.
- **Performance and stability.** Map movement and auto-walk avoid duplicate font,
  sight and terrain work; repeated log layout, plant lighting and image transfer
  copies are cached. A crash after adjacent melee was fixed. A fixed 24-step local
  sample measured action-settlement-plus-refresh median **44.501 ms → 36.173 ms**;
  this is a development-machine measurement, not a general frame-rate guarantee.
- **Bilingual fixes.** English coverage, live language switching, status strips,
  key table, settings pages and several residual Chinese strings were corrected.

## Download and install

- **Windows:** extract the ZIP and run `Oneirscript.exe`.
- **Linux:** extract the TAR.GZ and run `./launch-game.sh` in a graphical desktop.
- **macOS:** choose Apple Silicon or Intel, extract the ZIP, and open
  `Oneirscript.app`. Builds are unsigned and not notarized; if macOS blocks the
  first launch, use System Settings → Privacy & Security → Open Anyway, or
  Control-click the app and choose Open.

Keep `assets`, `vendor` and the supplied configuration beside the game. Desktop
packages include their terminal and fonts; Python is not required. Back up your
existing save directory before changing versions.

## Source and checksums

- `Oneirscript-v0.1.1-20261101-desktop-source.zip` is the corresponding source
  archive for this release. It was produced from development snapshot
  `d553842a34ec7d4f74b5c8c296f6b08daf9ffa7c`.
- This repository's tracked source baseline remains the v0.1.0 desktop snapshot;
  the v0.1.1 release assets above are the authoritative binaries and source for
  the 0.1.1 build.
- `RELEASE-MANIFEST.json` records size, SHA-256, version and architecture for each
  asset; `SHA256SUMS.txt` is a plain checksum list.

## Python distributions

The v0.1.1 release focuses on the desktop packages and their source archive.
The Python 3.11+ wheel and source distribution remain available in the
[v0.1.0 release](https://github.com/dis5mZl1e/oneirscript/releases/tag/v0.1.0).

---

## 中文摘要

本次 0.1.1 更新重点：首次入梦六步介绍；行囊五格网格与图标/稀有度/物品详情；
地图缩放、PUA 字形与植物/材料/气体/液体重绘；键位表和篡改编辑器说明；
发射源卡片、弹匣与手动装填；移动/自动行走与渲染缓存、贴身战斗闪退修复。
完整记录见仓库 `CHANGELOG.md`。桌面包含随包 WezTerm 与字体，无需安装 Python；
macOS 包未签名，首次打开按“仍要打开”处理。v0.1.1 Release 以桌面包和对应源码
ZIP 为主，Python wheel/sdist 仍见 v0.1.0 Release。
