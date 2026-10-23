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
- [AI-assisted development, forks, and contribution review](#en-ai-policy)

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
