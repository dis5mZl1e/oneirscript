# Oneirscript / 梦层

> *Rewrite the dream. Face what follows.*
>
> A traditional roguelike where words reshape reality and the environment becomes part of your tactics.

**Single-player · Turn-based · Procedural generation · Terminal game · Python**

[简体中文](README_CN.md) · English · [Project home](README.md)

<a id="en"></a>

**Contents**

- [About the game](#en-overview)
- [Core features](#en-features)
- [Downloads](#en-download)
- [Getting started](#en-play)
- [Running from source](#en-source)
- [Feedback and contributions](#en-contribute)
- [License](#en-license)

<a id="en-overview"></a>

## About the game

**Oneirscript is a traditional roguelike set in the subconscious.** Wake in the Origin of the Dream, explore shifting dreamscapes, confront wandering anomalies, and follow scattered memories toward the obsessions at their core.

Each action can change the situation. Crossing a pool, making a sound, or altering a sentence may open a route or set off an unexpected chain of events. Combat, observation, environmental interactions, and language all shape your options.

The game is under active development. It is built in Python with Textual, runs primarily in a terminal, and offers Chinese and English interfaces.

[Back to contents](#en) · [简体中文](README_CN.md#zh-overview)

<a id="en-features"></a>

## Core features

| System | What you can do |
|---|---|
| **Explore dreams** | Navigate generated rooms, caves, corridors, and mazes. Discover anomalous sites and enter self-contained dreams within dreams. |
| **Tamper with reality** | Edit descriptions of the environment or dialogue. Choose words and conditions, preview the resulting sentence, and weigh the costs and risks. |
| **Learn conceptions** | Find specific abilities that offer new ways to handle combat, exploration, and unusual environmental situations. |
| **Use the environment** | Bring liquids, gases, fire, electric fields, and material reactions into your tactics, reshaping local conditions and routes. |
| **Build your character** | Combine equipment-board entries, configure memory shards, and learn insights while balancing resources and adaptability. |
| **Observe, then act** | Examine targets and terrain before choosing melee, ranged fire, a throw, or a retreat. Turn-based play gives you time to think. |

Mind, lucidity, and imagination serve different purposes. Portents, noise, and chaos also affect the situation. Items, NPCs, events, a codex, and records of past dreams accompany your exploration.

[Back to contents](#en) · [简体中文](README_CN.md#zh-features)

<a id="en-download"></a>

## Downloads

**Download links are reserved for the official release and will be added later.**

| Platform | Download link |
|---|---|
| Windows | Coming later |
| macOS | Coming later |
| Linux | Coming later |

<!-- Add verified release links to the table above when publishing. No URLs yet. -->

Available platforms, architectures, and requirements will be listed with each release. Complete portable releases will include the terminal and fonts needed by the game. Source instructions are below.

[Back to contents](#en) · [简体中文](README_CN.md#zh-download)

<a id="en-play"></a>

## Getting started

1. Download a complete release for your platform and extract the entire archive. Keep its bundled resources, including `assets` and `vendor`.
2. Use the included game launcher. The game prefers bundled WezTerm with its dedicated font configuration; a compatibility launch option remains available for other terminals.
3. Start a new game and use the layer 0 tutorial to learn observation, actions, and environmental interactions before exploring further systems.

**Bundled WezTerm is recommended.** It provides the intended fonts and image-map display through a game-specific window configuration, separate from your global settings. Other terminals can use the character map; font, color, and mouse behavior depend on terminal support.

| Common action | Control |
|---|---|
| Move | Arrow keys / `WASD` |
| Wait | `.` |
| Pick up | `G` |
| Open or close the full control list | `Alt+H`, or click the control-list entry in the side panel |
| Expand or collapse the footer | `Alt+Z`, or click its expand button |

Use in-game prompts and the full control list for context-specific actions. Language, audio, and display options are available in Settings. Back up your saves before updating.

[Back to contents](#en) · [简体中文](README_CN.md#zh-play)

<a id="en-source"></a>

## Running from source

Use **Python 3.11 or newer**. After obtaining the source, run these commands from the project root. A virtual environment keeps the dependencies separate from your system Python.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_demo.py
```

**macOS / Linux**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_demo.py
```

Append `--compat-terminal` to the launch command to stay in the current terminal. Installing source dependencies requires network access. A source checkout may not include a portable terminal for your platform.

Developers can run a noninteractive smoke check with a separate save directory:

```bash
python run_demo.py --smoke --save-dir save-smoke
```

The native Windows build entry point is maintained in the development repository: [build.py](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/build.py). See [CONTRIBUTING.md](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/CONTRIBUTING.md) for development conventions.

[Back to contents](#en) · [简体中文](README_CN.md#zh-source)

<a id="en-contribute"></a>

## Feedback and contributions

Bug reports, play experiences, translations, new content, and code improvements are welcome. Use the issue tracker and pull or merge requests on the platform hosting this repository.

For a bug report, include the game version, operating system, terminal, reproduction steps, and expected versus actual behavior. Screenshots and error logs help. Check saves and logs for personal information before sharing them.

- [Contributing guide](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/CONTRIBUTING.md): development and submission conventions.
- [Code of conduct](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/CODE_OF_CONDUCT.md): community participation.
- [Security policy](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/SECURITY.md): vulnerability reporting; do not disclose security details in public issues.
- [Changelog](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/CHANGELOG.md): recorded version changes.

The full test suite and development tools are maintained in the original development repository and are not included in this source-only repository. Contribution checks are described in the contributing guide.

[Back to contents](#en) · [简体中文](README_CN.md#zh-contribute)

<a id="en-license"></a>

## License

**Project-owned code is licensed under [GNU GPL version 3 only (GPL-3.0-only)](LICENSE).** Commercial use, modification, and redistribution are permitted under its terms, including the applicable Corresponding Source requirements when distributing covered programs and modifications.

Fonts, icons, original audio, WezTerm, and other third-party components retain their separate licenses. See [LICENSING.md](LICENSING.md) for the boundaries and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for sources and notices.

Copyright (c) 2026 dis5mZl1e. The code license does not imply official endorsement or unrestricted use of the project's identity and marks.

[Back to contents](#en) · [简体中文](README_CN.md#zh-license)
