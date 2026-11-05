# Oneirscript 0.1.2 — English Changelog

**Released:** 2026-11-05  
**Downloads:** [GitHub Release v0.1.2](https://github.com/dis5mZl1e/oneirscript/releases/tag/v0.1.2)

The English build ships on Windows, Linux, macOS Apple Silicon and macOS Intel. The Chinese build is Windows-only for this release.

This update continues the authoritative-simulation and performance work and adds remote overwrite events, sidebar/input updates and stability fixes.
Release scope: the English build ships on Windows, Linux, macOS Apple Silicon and macOS Intel; the Chinese build is Windows-only for this release. A corresponding source archive and checksums accompany the Release.

#### Simulation and performance

- Continued work on authoritative material arrays, mutation records, native hot stages, separate simulation/presentation, incremental UI/map updates and image transport. Default rules, save format and existing switches remain compatible; unfinished items and measurements are documented in the development repository.
- Material settlement, visibility/glow, pathfinding and query caches gained dependency versions and conservative fallbacks; some new paths remain optional experiments.
- Incremental map/UI updates, log layout and native image transfer reduce repeated work; local timings are not presented as full acceptance.

#### Gameplay

- Added structured remote overwrite events with a 40-round cadence.
- Added regressions for zero-imagination and insufficient-resource edges so invalid actions are not silently accepted.

#### Interface and controls

- Continued sidebar workspace, keyboard/mouse routing, context-action and settings updates; improved reading and reachability for tasks, codex, inventory and hints.
- Continued English copy, key-table and residual-string coverage.

#### Stability

- Fixed crashes and lifecycle issues found during the simulation/presentation migration, with runtime error records and regression coverage.
- Older saves remain readable; back up saves before updating.


## Downloads

| Platform | Package |
|---|---|
| Windows x64 | [Oneirscript-v0.1.2-20261105-Windows-x86_64-en.zip](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/Oneirscript-v0.1.2-20261105-Windows-x86_64-en.zip) |
| Linux x64 | [Oneirscript-v0.1.2-20261105-Linux-x86_64-en.tar.gz](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/Oneirscript-v0.1.2-20261105-Linux-x86_64-en.tar.gz) |
| macOS Apple Silicon | [Oneirscript-v0.1.2-20261105-macOS-arm64-en.zip](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/Oneirscript-v0.1.2-20261105-macOS-arm64-en.zip) |
| macOS Intel | [Oneirscript-v0.1.2-20261105-macOS-Intel-en.zip](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/Oneirscript-v0.1.2-20261105-macOS-Intel-en.zip) |
| Python 3.11+ | [oneirscript-0.1.2-py3-none-any.whl](https://github.com/dis5mZl1e/oneirscript/releases/download/v0.1.2/oneirscript-0.1.2-py3-none-any.whl) |

## Installation

- **Windows:** extract the ZIP and run `Oneirscript.exe`.
- **Linux:** extract the TAR.GZ and run `./launch-game.sh` in a graphical desktop.
- **macOS:** choose Apple Silicon or Intel, extract the ZIP, and open `Oneirscript.app`. Builds are unsigned and not notarized; if macOS blocks the first launch, use System Settings → Privacy & Security → Open Anyway, or Control-click the app and choose Open.
- **Python:** install the wheel in a Python 3.11+ virtual environment and run `oneirscript`.

Keep `assets`, `vendor`, and the supplied configuration beside the game. Back up saves before updating.

## Source and checksums

- `Oneirscript-v0.1.2-20261105-desktop-source.zip` is the corresponding desktop source.
- `RELEASE-MANIFEST.json` records size, SHA-256, version, platform and architecture; `SHA256SUMS.txt` is a plain checksum list.
- The source tag for this release is `desktop-source-v0.1.2`.

## License

Project-owned code is licensed under **[GPL-3.0-only](LICENSE)**. Fonts, icons, audio, WezTerm and other third-party components retain their separate licenses; see [LICENSING.md](LICENSING.md) and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
