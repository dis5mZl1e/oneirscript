# Oneirscript 0.1.1 — English Changelog

**Released:** 2026-11-01  
**Downloads:** [GitHub Release v0.1.1](https://github.com/dis5mZl1e/oneirscript/releases/tag/v0.1.1)

Oneirscript 0.1.1 focuses on desktop map responsiveness, inventory and combat controls, and a clearer first run. It also expands the glyph and font set, improves English coverage, and fixes several stability issues.

## Introduction and help

- A new regular save opens a six-step introduction covering the game, arrow-key and numpad movement, WASD and `/` panel controls, travel without stairs, equipment sentences, tampering, and combat. It explains `N` to descend, `B` to ascend, and the requirement of 100 dissolution before descending.
- The introduction can be paged or dismissed without spending a turn. It does not appear in the playable tutorial and does not return automatically when loading or retrying a save. Reopen it from **Settings → Data → Entering the Dream**. Complete Chinese and English text is included.
- Both tamper editors now provide a gameplay guide covering targets, words, conditions, scope, costs, chaos, risks, and exiting. The guide reuses the association-board information window; reading or closing it does not submit an edit.

## Inventory and builds

- The inventory defaults to five square slots per row and extends as capacity grows. A vertical list layout remains available through the title-bar control, Enter, or `-` / `=` while the right inventory region is focused.
- Slot backgrounds represent item categories, with thin rarity borders. The wooden selection frame, corner mounts, and subtle creases were refined. New settings control the inventory border style and icon style.
- Large icons are typeset directly from font outlines at their final size and follow the PUA/common character setting. Quantity labels sit at the lower right with transparent text; the equipped star moves to the upper right and is enlarged. Item details appear above the grid, with clearer hierarchy for name, quantity, and a collapsible description.
- Grid scrolling, left-click use, border alignment, quantity/icon overlap, and missing equipment markers were fixed. Using an item keeps the inventory open.
- Large icons and creased frames no longer fall back after opening windows, switching pages, or compressing sidebar text. Graphics layers can retry or rebuild after a transient failure.
- Construct cards use category-specific backgrounds and explain their type and effects in the details. Clicking a card selects it; the separate **Cast** button or Enter activates it.
- Linked Memory details gain a **Return to Memory** link at the top, returning home from any detail depth. Association-board column syntax visibility was improved, catalog placeholders were replaced with descriptions, and selected long names and their English translations were shortened.

## Map, glyphs, and feedback

- Map zoom and full-map controls were added to the desktop top bar, with click and `(` / `)` support. 125% and 150% zoom levels complement the default scale.
- PUA is now the default character style. Selected plant and material glyphs were redrawn for clearer silhouettes, joined details, and readability, and detached shapes were removed.
- Gas concentration is rendered at three levels with distinct dot densities in the upper tile area. Each liquid uses its own glyph and concentration lines along the bottom of double-width tiles, reducing overlap with other layers.
- Stray color lines beneath some walls and after anomalies disappear were removed. Clipped emoji and PUA characters, missing-glyph boxes, and floating messages covered by the map were fixed.
- The Environment tab icon was replaced. Events and NPCs now use sparse, muted character animations to reduce oversized yellow markers and glow.

## Firing and reloading

- The firing screen is organized into sections with source cards and statistics. Magazine icons, remaining ammunition, and available totals are shown, with a clickable manual reload control.
- Firing reuses the last selected source. After a magazine runs empty, the next aim attempt tries to reload at the normal turn cost; aim again after the reload message to fire. Exhausted consumable projectiles advance to the next available source in order.
- `R` opens source selection when no empty-magazine weapon needs reloading. Reload attempts require an open firing or source-selection screen and a reloadable magazine.
- The right tamper editor gains confirm and cancel controls while keeping the preview, confirmation, and cost-payment flow.

## Stability and performance

- A crash that could occur while moving after a melee attack against an anomaly was fixed, with runtime error reporting and regression coverage.
- Movement and automatic walking now do less repeated font checking, visibility-ray work, and sight-range calculation. Terrain glyphs are cached within a frame, hidden and remembered map cells are reused, and unchanged regions are not redrawn.
- Repeated log layout is cached, and plant-light queries plus redundant copies during native graphics decoding and transport are reduced. Turn settlement, information visibility, and default visual quality are preserved.
- In a local 24-move WezTerm comparison, median action-plus-refresh time decreased from 44.501 ms to 36.173 ms. This is neither a display frame rate nor a guarantee for every scene. Detailed measurement notes are kept in the development repository.
- Misaligned English resource bars, empty plant values interrupting turns, first-frame image-layer initialization, and the sidebar returning to its default page after container fill or pour actions were fixed.
- A small clean-water spray now uses 3 units and costs 3 imagination; the twin hairdryer remains at 6.
- Regression and probe compatibility were updated: allocation sampling that could crash Python 3.11 probes is disabled, platform-specific cases are skipped where appropriate, and glyph and scrolling-viewport expectations were synchronized.

## Other improvements

- Quality-of-life and keyboard/mouse access: Alt replaces Ctrl for terminal compatibility, aiming uses a unified transaction, the footer uses a single line, and the side panel is responsive.
- Balance tuning toward less predictable situations: floor effects, skills, propagation, and psychological resource bands were rebalanced, with instability banners when crossing bands.
- Fourth batch of environmental reaction entries, covering all registered liquid and gas types.

## Web

- Image maps, layout, tampering, catalog, and font updates for the web client are recorded separately in the [Web 0.1.1 changelog](docs/web-0.1.1-changelog.en.md). The web frontend source is maintained in the development repository and is not part of this desktop-source repository; no separate web release package was produced.

## Downloads

| Platform | Package |
|---|---|
| Windows x64 | [Oneirscript-v0.1.1-20261101-Windows-x86_64-en.zip](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.1/Oneirscript-v0.1.1-20261101-Windows-x86_64-en.zip) |
| Linux x64 | [Oneirscript-v0.1.1-20261101-Linux-x86_64-en.tar.gz](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.1/Oneirscript-v0.1.1-20261101-Linux-x86_64-en.tar.gz) |
| macOS Apple Silicon | [Oneirscript-v0.1.1-20261101-macOS-arm64-en.zip](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.1/Oneirscript-v0.1.1-20261101-macOS-arm64-en.zip) |
| macOS Intel | [Oneirscript-v0.1.1-20261101-macOS-Intel-en.zip](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.1/Oneirscript-v0.1.1-20261101-macOS-Intel-en.zip) |
| Python 3.11+ | [oneirscript-0.1.1-py3-none-any.whl](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.1/oneirscript-0.1.1-py3-none-any.whl) |

The release also provides the [corresponding desktop source](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.1/Oneirscript-v0.1.1-20261101-desktop-source.zip), [RELEASE-MANIFEST.json](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.1/RELEASE-MANIFEST.json), and [SHA256SUMS.txt](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.1/SHA256SUMS.txt).

## Installation

- **Windows:** extract the ZIP and run `Oneirscript.exe`.
- **Linux:** extract the TAR.GZ and run `./launch-game.sh` in a graphical desktop.
- **macOS:** choose Apple Silicon or Intel, extract the ZIP, and open `Oneirscript.app`. Builds are unsigned and not notarized; if macOS blocks the first launch, use System Settings → Privacy & Security → Open Anyway, or Control-click the app and choose Open.
- **Python:** install the wheel in a Python 3.11+ virtual environment and run `oneirscript`. The first normal launch may download the external WezTerm terminal; `oneirscript --compat-terminal` stays in the current terminal.

Keep `assets`, `vendor`, and the supplied configuration beside the game. Desktop packages include their terminal and fonts; Python is not required for desktop play. Back up your save directory before changing versions.

## Source and checksums

- Version, platform, architecture, size, and SHA-256 for every asset are recorded in `RELEASE-MANIFEST.json`; `SHA256SUMS.txt` provides a plain checksum list.
- The corresponding desktop source is provided as `Oneirscript-v0.1.1-20261101-desktop-source.zip`. The public repository main branch contains the same v0.1.1 desktop source with the Python-installation adapters.
- The source tag for this release is `desktop-source-v0.1.1`.

## License

Project-owned code is licensed under **[GPL-3.0-only](LICENSE)**. Fonts, icons, original audio, WezTerm, and other third-party components retain their separate licenses; see [LICENSING.md](LICENSING.md) and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
