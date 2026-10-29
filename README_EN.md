# Oneirscript / 梦层

![Oneirscript — generated dreamscape](assets/readme/banner-1920x640.png)

> *Rewrite the dream. Face what follows.*
>
> A traditional roguelike where words reshape reality and the environment becomes part of your tactics.

**Traditional roguelike · Single-player · Turn-based grid tactics · Procedural generation · Permadeath**

[简体中文](README_CN.md) · English · [Project home](README.md)

<a id="en"></a>

**Contents**

- [About the game](#en-overview)
- [Screenshots and gameplay](#en-gallery)
- [Core features](#en-features)
- [Downloads](#en-download)
- [Getting started](#en-play)
- [Running from source](#en-source)
- [Technical overview](#en-technical)
- [Feedback and contributions](#en-contribute)
- [License](#en-license)
- [AI-assisted development, forks, and contribution review](#en-ai-policy)

<a id="en-overview"></a>

## About the game

**Oneirscript is a traditional roguelike set in the subconscious: grid-based exploration, turn-based actions, procedural generation, and permadeath that ends a run.** Wake in the Origin of the Dream, explore shifting dreamscapes, confront wandering anomalies, and follow scattered memories toward the obsessions at their core. Observation, positioning, resource management, and an understanding of the rules shape how far you get.

**Compose the rules of your actions, then rewrite the reality around you.** Arrange equipment-board entries into sentences with conditions, targets, and actions. Choose editable words in environmental descriptions or dialogue, preview the result, pay its cost, and see how it changes the situation. Liquids, gases, fire, light, and sound provide the tactical conditions those choices act upon.

The run follows a loop: **observe and explore → resolve encounters, events, and environmental problems → adjust your build → accumulate dissolution → decide whether to keep searching or descend**. Judge when to fight, when to take another route, when to spend resources rewriting a situation, and when to leave a stratum with what you have found.

The game is under active development. It is built in Python with Textual, runs primarily in a terminal, and offers Chinese and English interfaces.

[Back to contents](#en) · [简体中文](README_CN.md#zh-overview)

<a id="en-gallery"></a>

## Screenshots and gameplay

### Environmental chain reactions

Fire, explosions and electric fields unfolding through a prepared scene rendered by the real game engine.

![Engine-staged environmental chain reactions](assets/readme/environment-chain.gif)

### Rewrite a real encounter

English desktop gameplay: select a tampering word, preview the edit and its cost, then apply it on a generated combat map.

![English desktop reality-tampering demonstration](assets/readme/tamper-desktop-en.gif)

### Compose an equipment sentence

English desktop gameplay: pick up, move and rotate equipment, place a function word, then use the resulting build in combat.

![English desktop equipment-board demonstration](assets/readme/equipment-desktop-en.gif)

### A wider dreamscape

![Omniscient overview of a generated dream map](assets/readme/background-full-map-itch.png)

Development captures may differ from this source snapshot. The overview uses omniscient framing; the environmental demonstration is staged in-engine. Tampering and equipment GIFs were recorded in the desktop game on generated maps. [Capture notes](assets/readme/README.md).

<a id="en-features"></a>

## Core features

| Distinctive system | What makes it interesting to play |
|---|---|
| **Build with sentences** | Arrange conditions, targets, and actions on the equipment board, read the resulting sentence, and try the combination in play. Build decisions involve triggers, affected targets, and additional effects. |
| **Use tampering as a tactical action** | Edit eligible parts of nearby environmental descriptions or dialogue, preview the result, then weigh imagination costs, chaos, and risk. Decide what is worth changing, when to change it, and what resources to save for later threats. |
| **Work with interacting environments** | Use sound to lure, light and cover to judge routes, and conductive pools, spreading fire, and liquid–gas reactions to deal with enemies and terrain. Several systems can contribute to the same encounter. |
| **Find solutions in generated situations** | Generated rooms, caves, corridors, and mazes combine with different anomalies, supplies, and anomalous sites to change your routes, encounters, and available tools. |
| **Follow branching dreams and choices** | Enter self-contained dreams within dreams, engage with NPCs, events, mechanisms, and side objectives, and approach the core obsessions and different endings. |
| **Learn the rules through observation** | Examine threats through observation, the codex, and detailed views. Adapt with conceptions, memory shards, and insights, and take what you have learned into your next attempt. |

Mind, lucidity, and imagination serve different purposes. Portents, noise, and chaos also affect the situation. The challenge is to make choices with this run's equipment, abilities, and environment, finding solutions whose costs you can afford.

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

These are the default common controls. Letter keys are shown in uppercase and do not require Shift. Aiming, editors, dialogs, and panels take priority according to the current context.

| Key | Action |
|---|---|
| `Arrow keys / Numpad` | Move on the map; numpad supports diagonals |
| `WASD` | Select entries and switch categories in the side panel |
| `/` | Switch focus between map and panel |
| `.` | Wait one turn |
| `Enter` | Act / Confirm the current selection |
| `G / E` | Pick up items / Interact with a site or object |
| `Tab` | Open inventory; while aiming, switch to a free target cell |
| `U` | Use an item; items can also be selected and confirmed in inventory |
| `F` | Aim; press again while aiming to view firing sources |
| `O` | Cycle valid enemy targets while aiming |
| `Q` | Aim a throw; return from a panel |
| `R` | Reload the current firing source |
| `X` | Observe; Enter travels to the selected cell while observing |
| `Right-click` | Inspect a cell or item / Open context actions |
| `H / ?` | Actions and help; select available conceptions and other actions |
| `T / [` | Equipment page / Equipment-board editor |
| `C` | Tamper with eligible dialogue or nearby descriptions |
| `V / I / K` | Portents / Insights / Observations |
| `J` | Quest journal |
| `Alt+S / Alt+N` | Character details / Noise and chaos details |
| `F3` | Layered observation; Tab switches layers within that view |
| `N / B` | Descend when eligible / Backtrack |
| `Esc` | Cancel or return; pause when no action or view needs cancelling |
| `F10` | Save and return home; press again on the main home screen to exit |
| `Alt+H / Alt+Z` | Full controls reference / Expand or collapse the footer |

**Use arrow keys or the numpad for character movement; WASD primarily operates the side panel.** Use `/` to switch map/panel focus. Left-click selects, moves, or acts; the wheel scrolls lists. Press `Alt+H` for the full reference, and follow in-game prompts and settings for context-specific behavior.

Language, audio, and display options are available in Settings. Back up your saves before updating.

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

For code navigation and development checks, read [TECHNICAL_EN.md](TECHNICAL_EN.md). Build scripts for native release packaging are not part of this checkout.

[Back to contents](#en) · [简体中文](README_CN.md#zh-source)

<a id="en-technical"></a>

## Technical overview

The game uses Python 3.11+, Textual/Rich, NumPy, Pillow/FontTools, asciimatics and pygame, with WezTerm as the recommended terminal. Session commands connect the UI to game rules; board compilation, tamper settlement, environmental simulation and map presentation are organized as distinct systems.

See the [technical overview](TECHNICAL_EN.md) for the architecture diagram, source map, system explanations and reproducible smoke-check commands. This source-focused checkout does not include the web frontend, platform binaries, portable terminal vendor directory or full maintainer test/build tools.

<a id="en-contribute"></a>

## Feedback and contributions

Read [CONTRIBUTING.md](CONTRIBUTING.md), the primary English contribution guide,
for submission permissions, project direction, contributor review and merge
criteria. A [Chinese reference translation](CONTRIBUTING_CN.md) is also available.

Bug reports, play experiences, translations, new content, and code improvements are welcome. Use the issue tracker and pull or merge requests on the platform hosting this repository.

For a bug report, include the game version, operating system, terminal, reproduction steps, and expected versus actual behavior. Screenshots and error logs help. Check saves and logs for personal information before sharing them.


The full test suite and development tools are not included in this source-only repository. Available checks are described in the [technical guide](TECHNICAL_EN.md#development-checks); review requirements are in the [AI and contribution policy](#en-ai-policy) below.

[Back to contents](#en) · [简体中文](README_CN.md#zh-contribute)

<a id="en-license"></a>

## License

**Project-owned code is licensed under [GNU GPL version 3 only (GPL-3.0-only)](LICENSE).** Commercial use, modification, and redistribution are permitted under its terms, including the applicable Corresponding Source requirements when distributing covered programs and modifications.

Fonts, icons, original audio, WezTerm, and other third-party components retain their separate licenses. See [LICENSING.md](LICENSING.md) for the boundaries and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for sources and notices.

Copyright (c) 2026 dis5mZl1e. The code license does not imply official endorsement or unrestricted use of the project's identity and marks.

[Back to contents](#en) · [简体中文](README_CN.md#zh-license)

---

<a id="en-ai-policy"></a>

## AI-assisted development, forks, and contribution review

### Disclosure of AI assistance

AI tools have assisted with writing, modifying, and analyzing portions of this game's code. AI assistance is part of the development process; it does not mean that all code was generated by AI, nor does it guarantee correctness, security, originality, or the absence of third-party rights issues. The use of AI does not change the license applicable to any code or asset, or remove a contributor's responsibility to understand, review, and verify their contribution.

### Permission for independent forks and modifications

Anyone may create, maintain, and distribute open-source forks, modified versions, or other derivatives of this project, provided they comply with [GNU GPL version 3 only (GPL-3.0-only)](LICENSE) and the separate licenses of relevant assets. Creating or publishing such a version does not, by itself, require additional case-by-case approval from the original author. Preserve applicable copyright and license notices, identify modifications, and provide recipients with Corresponding Source where required by the GPL. This statement does not require all private modifications to be published to the public, or authorize relicensing GPL-covered derivatives under incompatible terms. Fonts, icons, audio, and other assets retain their respective licenses; see [licensing boundaries](LICENSING.md) and [third-party notices](THIRD-PARTY-NOTICES.md).

### Responsibility and identification of unofficial versions

An independent fork or modified version does not become an official release or receive the original author's endorsement merely because it derives from this project, publishes its source, or has submitted a pull request. When releasing such a version, clearly identify its maintainer, relationship to the original project, and modifications so that users are not led to believe it is released, reviewed, maintained, or supported by the original author.

Except where applicable law provides otherwise or the original author makes a separate written commitment, the original author does not undertake to review, maintain, update, or support independent forks or modified versions, or guarantee their functionality, stability, security, compatibility, or save integrity. Their use, distribution, or maintenance does not automatically create liability for the original author. Questions and support requests about those versions should first be directed to their actual maintainers. Warranty disclaimers and limitations of liability are governed by [LICENSE](LICENSE) and applicable law. This statement does not exclude liability that cannot lawfully be excluded, or guarantee that official versions are free of defects.

### AI-assisted contributions and pull requests

This project accepts AI-assisted code contributions that have undergone human review. Before submission, the contributor must perform a substantive human review and be able to explain how the code works, why it was changed, and its principal risks. AI self-review or confirmation alone does not satisfy this requirement.

Submissions should include:

- The problem addressed, implementation approach, scope of impact, and known limitations.
- Whether AI assistance was used and the main areas involved. Full prompts or conversation records containing personal information, credentials, or other sensitive material are not required.
- Confirmation of human review, along with the tests actually performed, environment, results, and any remaining unverified areas. Tests that were not run must not be reported as passing.
- The provenance and licenses of added or referenced code, dependencies, and assets. Contributors must confirm that they are entitled to submit the material under terms compatible with its inclusion in the project, without disclosing proprietary code, credentials, or personal information they are not authorized to share.

The original author will consider merging a proposed change into the main project only after performing the necessary testing and review. Passing tests is a prerequisite for consideration, not a promise of acceptance. Project direction, maintainability, security, compatibility, licensing compliance, and review cost also inform the decision. The author may request additional information, changes, or smaller submissions, or defer or decline a merge, without committing to a fixed review or merge schedule. Submitting a pull request does not automatically transfer the contributor's copyright or make the author responsible for maintaining the independent fork.

### Scope of this statement

These contribution requirements apply to changes submitted for inclusion in this project. They do not impose additional restrictions on the independent use, modification, and distribution rights granted by the GPL, or require independent forks to adopt this project's review process. Applicable licenses and third-party notices must be respected whether or not AI is used. This section describes development practices, responsibility boundaries, and contribution procedures; it does not replace or amend the licenses. Rights and obligations are governed by [LICENSE](LICENSE), applicable asset licenses, and applicable law.

[Back to contents](#en) · [简体中文](README_CN.md#zh-ai-policy)
