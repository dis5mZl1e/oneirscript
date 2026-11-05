# Oneirscript 0.1.2 — English Changelog

**Released:** 2026-11-05  
**Release:** [GitHub Release v0.1.2](https://github.com/dis5mZl1e/oneirscript/releases/tag/v0.1.2)

Oneirscript 0.1.2 continues the authoritative-simulation and performance work, adds structured remote overwrite events, and updates sidebar, input and stability work.

**Release scope:** the English build ships on Windows x64, Linux x64, macOS Apple Silicon and macOS Intel. The Chinese build is Windows-only for this release.

## Simulation and performance

- Continued work on authoritative material arrays, mutation records, native hot stages, separate simulation and presentation, incremental UI/map updates, and image transport. Default rules, save format and existing switches remain compatible. Some new paths remain optional experiments; unfinished items and measurements are documented in the development repository.
- Material settlement, visibility and glow, pathfinding and query caches gained dependency versions and conservative fallbacks, so unrelated world changes do not silently reuse stale results.
- Incremental map and UI updates, log layout, and native image transfer reduce repeated work. Local timings are not presented as full acceptance or a universal frame-rate guarantee.

## Gameplay

- Added structured remote overwrite events with a 40-round cadence.
- Added regressions for zero-imagination and insufficient-resource edges, so invalid actions are not silently accepted.

## Interface and controls

- Continued sidebar workspace, keyboard and mouse routing, context-action and settings updates. Tasks, codex, inventory and hints received readability and reachability improvements.
- Continued English copy, key-table and residual-string coverage.

## Stability

- Fixed crashes and lifecycle issues found during the simulation and presentation migration, with runtime error records and regression coverage.
- Older saves remain readable. Back up saves before updating.

## Downloads

| Platform | Package |
|---|---|
| Windows x64 | [Oneirscript-v0.1.2-20261105-Windows-x86_64-en.zip](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/Oneirscript-v0.1.2-20261105-Windows-x86_64-en.zip) |
| Linux x64 | [Oneirscript-v0.1.2-20261105-Linux-x86_64-en.tar.gz](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/Oneirscript-v0.1.2-20261105-Linux-x86_64-en.tar.gz) |
| macOS Apple Silicon | [Oneirscript-v0.1.2-20261105-macOS-arm64-en.zip](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/Oneirscript-v0.1.2-20261105-macOS-arm64-en.zip) |
| macOS Intel | [Oneirscript-v0.1.2-20261105-macOS-Intel-en.zip](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/Oneirscript-v0.1.2-20261105-macOS-Intel-en.zip) |
| Python 3.11+ | [oneirscript-0.1.2-py3-none-any.whl](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/oneirscript-0.1.2-py3-none-any.whl) |

The release also includes the [corresponding desktop source](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/Oneirscript-v0.1.2-20261105-desktop-source.zip), [RELEASE-MANIFEST.json](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/RELEASE-MANIFEST.json), and [SHA256SUMS.txt](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/SHA256SUMS.txt). The Chinese Windows package is `Oneirscript-v0.1.2-20261105-Windows-x86_64-zh.zip`.

## Installation

- **Windows:** extract the ZIP and run `Oneirscript.exe`.
- **Linux:** extract the TAR.GZ and run `./launch-game.sh` in a graphical desktop.
- **macOS:** choose Apple Silicon or Intel, extract the ZIP, and open `Oneirscript.app`. Builds are unsigned and not notarized; if macOS blocks the first launch, use System Settings → Privacy & Security → Open Anyway, or Control-click the app and choose Open.
- **Python:** install the wheel in a Python 3.11+ virtual environment and run `oneirscript`.

Keep `assets`, `vendor` and the supplied configuration beside the game. Desktop packages include their terminal and fonts; Python is not required for desktop play. Back up saves before updating.

## Source and checksums

- The corresponding desktop source is `Oneirscript-v0.1.2-20261105-desktop-source.zip`, built from development snapshot `0df1867c`. The main branch is synchronized to v0.1.2 and the `desktop-source-v0.1.2` tag records it.
- `RELEASE-MANIFEST.json` records version, platform, architecture, size and SHA-256 for every asset; `SHA256SUMS.txt` is a plain checksum list.

## License

Project-owned code is licensed under **[GPL-3.0-only](LICENSE)**. Fonts, icons, audio, WezTerm and other third-party components retain their separate licenses; see [LICENSING.md](LICENSING.md) and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
