# 梦层 / Oneirscript

![Oneirscript — generated dreamscape](assets/readme/banner-1920x640.png)

*Rewrite the dream. Face what follows.*

**[简体中文](README_CN.md) · [English](README_EN.md) · [Download v0.1.0 / 下载](https://github.com/dis5mZl1e/oneirscript/releases/tag/v0.1.0)**

**传统 Roguelike · 网格回合制 · 程序生成 · 失败重开**

**Traditional roguelike · Turn-based grid tactics · Procedural generation · Permadeath**

梦层是一款以潜意识为舞台的传统 Roguelike。观察局势、管理资源，在随机生成的梦境里寻找通路。你可以**把装备组织成行动语句、改写眼前现实的描述，再利用材料、光照和声音解决遭遇**。

Oneirscript is a traditional roguelike set in the subconscious. Read the situation, manage resources, and find your way through generated dreamscapes. **Compose equipment into action sentences, rewrite descriptions of reality, and use materials, light, and sound to solve encounters.**

## 独特玩法 / What makes it distinctive

| 特色 / System | 玩点 | What you play with |
|---|---|---|
| **语法装备 / Equipment sentences** | 组合条件、目标和行为，改变自己的行动规则。 | Combine conditions, targets, and actions to shape the rules of your build. |
| **现实篡改 / Reality tampering** | 预览并修改可编辑描述，权衡想象力费用、混乱与风险。 | Preview and edit eligible descriptions, weighing imagination costs, chaos, and risk. |
| **环境战术 / Environmental tactics** | 利用声音诱引、光照遮挡、积液传导、火焰与液气反应。 | Work with sound lures, light and cover, conductive pools, fire, and liquid–gas reactions. |
| **梦境探索 / Dream exploration** | 选择路线，处理异象、事件和支线梦境，决定何时下潜。 | Choose routes, handle anomalies and events, explore branching dreams, and decide when to descend. |

**观察与探索 → 处理遭遇 → 调整构筑 → 累积崩解度 → 继续搜寻或下潜。** 根据本局得到的能力与环境找解法，失败后重新尝试。

**Observe and explore → resolve encounters → adjust your build → accumulate dissolution → keep searching or descend.** Find solutions with this run's abilities and surroundings, then learn from each attempt.

## 实机演示 / Gameplay

**环境连锁反应 / Environmental chain reactions**

![Engine-staged fire, explosions and electric fields](assets/readme/environment-chain.gif)

真实引擎布置场景，展示发生与蔓延过程。A prepared in-engine scene showing hazards developing and spreading.

**现实篡改 / Reality tampering**

![English desktop reality tampering on a generated combat map](assets/readme/tamper-desktop-en.gif)

英文桌面版，在生成的战斗地图中预览并执行改写。English desktop recording: preview and apply an edit during an encounter.

**语法装备 / Equipment sentences**

![English desktop equipment placement, rotation and function words](assets/readme/equipment-desktop-en.gif)

拿起、移动、旋转、放置功能词并展示效果。Pick up, move, rotate and place a function word, then put the build to work.

素材录自开发构建，可能与当前源码快照不同；详见 [素材说明 / capture notes](assets/readme/README.md)。

## 技术概览 / Technical overview

Python 3.11+ · Textual / Rich · NumPy · Pillow / FontTools · asciimatics · pygame · WezTerm

游戏会话将输入分派给规则与世界状态；装备语句、篡改结算、材料反应、地图生成与终端呈现分别组织。
篡改是本地规则系统，不依赖在线生成式 AI。

Session commands feed the rules and world state. Equipment compilation, tamper settlement, material reactions, map generation and terminal presentation have separate responsibilities. Reality tampering uses local rules rather than an online generative AI service.

| 技术文档 / Technical guide | 内容 / Contents |
|---|---|
| [中文技术介绍](TECHNICAL_CN.md) | 架构、代码导航、系统实现、运行检查与仓库范围 |
| [English technical guide](TECHNICAL_EN.md) | Architecture, code map, system implementation, development checks and repository scope |

本仓库提供 v0.1.0 桌面源码、字体、音频、特效资源和基础构建配方；发行包见 Releases。网页版、便携终端二进制和完整维护者工具链另行维护。
This repository contains v0.1.0 desktop source, runtime assets and basic build recipes. Releases provide the desktop binaries. The web frontend, portable terminal binaries and full maintainer toolchain are maintained separately.

## 阅读指南 / Guides

| 语言 / Language | 内容 / Contents |
|---|---|
| [简体中文 — README_CN.md](README_CN.md) | 游戏介绍、运行方式、操作与许可 |
| [English — README_EN.md](README_EN.md) | Overview, setup, controls, and licensing |
| [Contributing — English primary guide](CONTRIBUTING.md) | Submission permissions, review, design direction and merge decisions |
| [中文贡献指南（参考译文）](CONTRIBUTING_CN.md) | 提交权限、代码审查、设计偏好与分支建议 |

## 从源码运行 / Run from source

需要 Python 3.11 或更新版本。在仓库根目录执行：

Requires Python 3.11 or later. From the repository root:

```sh
python -m pip install -r requirements.txt
python run_demo.py
```

首次启动推荐的 WezTerm 终端可能需要联网下载。也可直接使用当前终端：

The recommended WezTerm terminal may need an internet connection on first launch. To use your current terminal:

```sh
python run_demo.py --compat-terminal
```

游戏内设置支持中文／英文切换。`game_config.ini` 提供启动配置，存档保存在本地 `save/`。

Chinese and English are available in the in-game settings. Startup options are in `game_config.ini`; saves are stored locally in `save/`.

## 操作 / Controls

默认常用键位；字母无须 Shift。按键随当前面板、瞄准或编辑状态变化。

Default common controls; letters do not require Shift. Active panels, aiming, and editors determine the context.

| 按键 / Key | 操作 | Action |
|---|---|---|
| `Arrow keys / Numpad` | 地图移动；小键盘支持斜向 | Move on the map; numpad supports diagonals |
| `WASD` | 右侧面板选择与分类切换 | Select entries and switch categories in the side panel |
| `/` | 切换地图／面板焦点 | Switch focus between map and panel |
| `.` | 等待一回合 | Wait one turn |
| `Enter` | 行动／确认当前选择 | Act / Confirm the current selection |
| `G / E` | 收纳物品／回应地点或对象 | Pick up items / Interact with a site or object |
| `Tab` | 打开行囊；瞄准时切到自由落点 | Open inventory; while aiming, switch to a free target cell |
| `U` | 使用物品；也可从行囊选择后确认 | Use an item; items can also be selected and confirmed in inventory |
| `F` | 进入瞄准；瞄准中再按查看发射来源 | Aim; press again while aiming to view firing sources |
| `O` | 瞄准时切换合法敌方目标 | Cycle valid enemy targets while aiming |
| `Q` | 投掷瞄准；面板中返回 | Aim a throw; return from a panel |
| `R` | 为当前发射来源换弹 | Reload the current firing source |
| `X` | 观察；观察时 Enter 前往选中位置 | Observe; Enter travels to the selected cell while observing |
| `Right-click` | 查看格子或物品详情／上下文操作 | Inspect a cell or item / Open context actions |
| `H / ?` | 操作与帮助；选择可用构想等行动 | Actions and help; select available conceptions and other actions |
| `T / [` | 携带意象页面／联想盘编辑器 | Equipment page / Equipment-board editor |
| `C` | 篡改可编辑的对话或眼前文字 | Tamper with eligible dialogue or nearby descriptions |
| `V / I / K` | 征兆／现实洞察／观测 | Portents / Insights / Observations |
| `J` | 任务日志 | Quest journal |
| `Alt+S / Alt+N` | 自我察觉／噪音与混乱详情 | Character details / Noise and chaos details |
| `F3` | 分层观察；观察内 Tab 切层 | Layered observation; Tab switches layers within that view |
| `N / B` | 满足条件后下潜／回溯 | Descend when eligible / Backtrack |
| `Esc` | 取消或逐级返回；无待取消状态时暂停 | Cancel or return; pause when no action or view needs cancelling |
| `F10` | 保存并返回主页；主页再按退出 | Save and return home; press again on the main home screen to exit |
| `Alt+H / Alt+Z` | 完整键位表／展开或收起底栏 | Full controls reference / Expand or collapse the footer |

**方向键／小键盘移动角色，WASD 主要操作右栏；`/` 切换焦点。** 左键选择／移动／行动，右键详情，滚轮滚动。

**Arrow keys / numpad move the character; WASD primarily operates the side panel. `/` switches focus.** Left-click selects / moves / acts, right-click inspects, and the wheel scrolls.

按 `Alt+H` 查看完整键位；以游戏内上下文提示与设置为准。Press `Alt+H` for the full reference; follow in-game prompts and settings.

## 许可 / License

[授权与 AI 贡献政策](#zh-ai-policy) · [Licensing and AI contribution policy](#en-ai-policy)

项目自有代码采用 [GPL-3.0-only](LICENSE)。字体、图标和音频保留各自的独立许可；详见 [许可边界](LICENSING.md)、[第三方声明](THIRD-PARTY-NOTICES.md)及 [音频署名](assets/CREDITS.md)。

Project-owned code is licensed under [GPL-3.0-only](LICENSE). Fonts, icons, and audio retain their separate licenses; see [licensing boundaries](LICENSING.md), [third-party notices](THIRD-PARTY-NOTICES.md), and [audio credits](assets/CREDITS.md).

---

<a id="zh-ai-policy"></a>

## AI 辅助开发、分支授权与贡献审核

### AI 辅助开发说明

本游戏的开发过程中使用了人工智能工具辅助编写、修改和分析部分程序代码。AI 辅助是本项目开发方式的一部分，不代表全部代码均由 AI 生成，也不构成对代码正确性、安全性、原创性或第三方权利状况的保证。是否使用 AI，不改变相关代码和资源各自适用的许可证，也不免除提交者对其贡献的理解、审核与验证责任。

### 独立分支与改版的授权

在遵守 [GNU GPLv3（GPL-3.0-only）](LICENSE)及相关资源独立许可的前提下，任何人均可创建、维护和分发本项目的开源分支、修改版或其他衍生版本，无须仅因创建或发布此类版本而另行取得原作者的逐项批准。修改和分发时，应保留适用的版权及许可声明，明确标示修改事实，并按 GPLv3 的适用要求向接收者提供对应源码。本说明不要求将仅供私人使用的修改一律向公众公开，也不授予将受 GPL 覆盖的衍生作品任意改为不兼容许可证的权利。字体、图标、音频等资源继续适用各自的许可，详见 [许可边界](LICENSING.md)与[第三方声明](THIRD-PARTY-NOTICES.md)。

### 非官方版本的责任与标识

独立分支和改版不因其来源于本项目、公开源代码或曾向本项目提交合并请求，即成为官方版本或获得原作者背书。发布此类版本时，请清楚说明其维护者、与原项目的关系及修改情况，避免使使用者误认为其由原作者发布、审核、维护或提供支持。

除适用法律另有规定或原作者另行作出书面承诺外，原作者不承诺审查、维护、更新或支持任何独立分支和改版，不保证其功能、稳定性、安全性、兼容性或存档完整性，也不因其使用、分发或维护情况而自动承担责任。此类版本的问题与支持请求应首先联系其实际维护者。软件的无担保及责任限制，以 [LICENSE](LICENSE)及适用法律为准；本说明不排除法律规定不得排除的责任，也不保证官方版本不存在缺陷。

### AI 辅助贡献与合并请求

本项目接受经过人工审核的 AI 辅助代码合并请求。提交者应在提交前完成实质性的人工检查，能够解释所提交代码的工作方式、修改目的和主要风险；仅由 AI 自行检查或确认，不视为已经完成人工审核。

提交时应提供以下信息：

- 修改所解决的问题、实现方式、影响范围及已知限制。
- AI 辅助的使用情况与主要涉及范围；无需提供包含个人信息、凭据或其他敏感内容的完整提示词或会话记录。
- 已完成人工审核的说明，以及实际执行的测试、运行环境、结果和仍未验证的部分。未执行的测试不得描述为已通过。
- 新增或引用代码、依赖和素材的来源及适用许可；提交者应确认有权提交相关内容，并以与项目相容的许可供项目接收，不得包含无权披露的专有代码、凭据或个人信息。

原作者仅会在对拟合并改动进行必要测试和审查后，才考虑是否将其合并至主项目。测试通过是考虑合并的必要条件，并不构成合并承诺；项目方向、可维护性、安全性、兼容性、许可合规和审核成本同样属于判断依据。作者可以要求补充材料、修改或拆分请求，也可以暂缓或拒绝合并，且不承诺固定的审核或合并时限。提交合并请求不自动转移提交者的著作权，也不意味着作者接受对独立分支的持续维护责任。

### 说明的适用范围

上述贡献要求适用于请求合并至本项目的改动，不构成对 GPL 所授予的独立使用、修改及分发权利的额外限制，也不要求独立分支沿用本项目的审核流程。无论是否使用 AI，许可证及第三方资源声明均应得到遵守。本节是开发方式、责任边界和贡献流程的说明，不替代或修改许可证正文；具体权利义务以 [LICENSE](LICENSE)、各资源适用的许可及适用法律为准。

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
