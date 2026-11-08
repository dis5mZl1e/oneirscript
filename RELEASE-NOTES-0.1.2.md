# Oneirscript v0.1.2

**Released:** 2026-11-05  
**Repacked:** 2026-11-08  
**Full English changelog:** [CHANGELOG_EN.md](https://github.com/dis5mZl1e/oneirscript/blob/main/CHANGELOG_EN.md)

English builds ship on Windows x64, Linux x64, macOS Apple Silicon and macOS Intel. The Chinese build is Windows-only for this release.

## What's new in 0.1.2

- **Authoritative simulation and performance work.** Continued work on authoritative material arrays, mutation records, native hot stages, separate simulation/presentation, incremental UI/map updates and image transport. Default rules, save format and existing switches remain compatible; unfinished items and measurements stay documented in the development repository.
- **Remote overwrite events.** Structured remote overwrite events now run on a 40-round cadence.
- **Interface and controls.** Sidebar workspaces, keyboard/mouse routing, context actions and settings continued to change, with better reading and reachability for tasks, codex, inventory and hints.
- **English coverage.** More English copy, key-table entries and residual interface strings were completed.
- **Stability.** Crashes and lifecycle issues from the simulation/presentation migration were fixed, with runtime error records and regression coverage.
- **Repack fixes.** Equipment-board relational rows (OF/BY placement), board-editor scroll restoration and panel/toast behavior were corrected in the 2026-11-08 repack.

## Downloads

| Platform | Package |
|---|---|
| Windows x64 (English) | `Oneirscript-v0.1.2-20261108-Windows-x86_64-en.zip` |
| Linux x64 (English) | `Oneirscript-v0.1.2-20261108-Linux-x86_64-en.tar.gz` |
| macOS Apple Silicon (English) | `Oneirscript-v0.1.2-20261108-macOS-arm64-en.zip` |
| macOS Intel (English) | `Oneirscript-v0.1.2-20261108-macOS-Intel-en.zip` |
| Windows x64 (Chinese) | `Oneirscript-v0.1.2-20261108-Windows-x86_64-zh.zip` |

The Release also provides `Oneirscript-v0.1.2-20261108-desktop-source.zip`, the Python wheel/sdist, `RELEASE-MANIFEST.json` and `SHA256SUMS.txt`.

## Installation

- **Windows:** extract the ZIP and run `Oneirscript.exe`.
- **Linux:** extract the TAR.GZ and run `./launch-game.sh` in a graphical desktop.
- **macOS:** choose Apple Silicon or Intel, extract the ZIP, and open `Oneirscript.app`. Builds are unsigned and not notarized; if macOS blocks the first launch, use System Settings → Privacy & Security → Open Anyway, or Control-click the app and choose Open.
- **Python:** install the wheel in a Python 3.11+ virtual environment and run `oneirscript`.

Keep `assets`, `vendor` and the supplied configuration beside the game. Back up saves before updating.

## Source and checksums

- The corresponding source archive is built from development snapshot `a06f96d`; the main branch is synchronized to v0.1.2 and the `desktop-source-v0.1.2` tag records it.
- `RELEASE-MANIFEST.json` records version, platform, architecture, size and SHA-256 for every asset; `SHA256SUMS.txt` is a plain checksum list.

## 中文摘要

0.1.2 继续推进权威模拟与性能改造，并加入远程覆盖事件、侧栏/键鼠更新、英文文案与稳定性修复。发行范围：英文版提供 Windows / Linux / macOS（Apple Silicon、Intel）全平台包；中文版本次仅提供 Windows 包。对应源码包、Python 分发包与校验清单随 Release 提供。
