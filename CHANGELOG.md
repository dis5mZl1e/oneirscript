# 更新日志 / Changelog

[简体中文](#zh) · [English](#en)

<a id="zh"></a>

## 简体中文

本项目的所有显著变更都记录在本文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。
提交粒度的完整开发历史由开发仓库维护；本仓库保留公开源码基线与发行文档。

### [Unreleased]

无未发布改动；以下 0.1.1 条目均已进入发行版。 / No unreleased changes; the 0.1.1 entries below shipped in the release.

### [0.1.1] - 2026-11-01

本次更新重点改善桌面端的地图流畅度、行囊与战斗操作，并补充首次入梦介绍。
0.1.1 于 2026-11-01 打包发行：Windows / Linux / macOS（Apple Silicon、Intel）中英共 8 个桌面包，另附对应源码包与校验清单。本仓库主分支源码同步至该版本，对应开发快照 `d553842a`；下载与校验见 [v0.1.1 Release](https://github.com/dis5mZl1e/oneirscript/releases/tag/v0.1.1)。

#### 首次入梦与玩法说明

- 普通新存档首次进入时增加六步简短介绍：游戏类型、方向键/数字键盘移动、WASD 与 `/` 界面控制、无楼梯的下潜/上浮、联想盘语句装备、篡改及战斗方式。说明 N 下潜、B 上浮，以及下潜需要崩解度达到 100。
- 入梦介绍可翻页或直接关闭，不消耗回合；新手教程不触发，读档和重试不再自动弹出。可从「设置 → 数据 → 入梦介绍」重新查看，中英文均提供完整文案。
- 左右篡改界面加入可点击的玩法说明，介绍目标、字词、条件、范围、代价、混乱风险与退出方式；复用联想盘说明浮窗，阅读和关闭不会提交修改。

#### 行囊与构筑界面

- 行囊默认使用每行五格的方形布局，容量增加时继续向后扩展；保留旧版竖排列表，可通过标题栏入口、Enter 或右侧区域中的 `-` / `=` 切换。
- 格子以物品种类着色，细边框表示稀有度；调整选中木色边框的宽度与配色，加深四角装裱线，并保留轻微折痕。设置新增行囊边框风格与图标风格选项。
- 大图标按最终尺寸绘制字体轮廓，支持 PUA 与常用字符；数量移至右下角并以透明文字叠加，装备星标移至右上角并放大。物品详情移至格子上方，整理名称、数量和可收起介绍的层次。
- 修复格子滚动、左键使用、边框对齐、数量与图标遮挡，以及部分联想盘装备未在行囊标记的问题。使用物品后留在行囊页。
- 修复窗口开关、页面切换及少字模式导致大图标和折痕边框回退的问题；图形图层暂时失败后可重试、重建。
- 构想按类型使用不同卡片底色，详情补充所属类型与类型效果；卡片正文点击只选择，独立「释放」按钮或 Enter 执行。
- 记忆超链接详情顶部增加「回到记忆页」，可从任意详情层级直接返回主页。改善联想盘列语法显示，补全图鉴介绍，清理占位文字并调整部分过长名称及英文译名。

#### 地图、字形与视觉反馈

- 桌面顶部增加地图缩放与全图查看入口，支持点击或 `(` / `)` 调整，补充 125% 与 150% 档位，保留原有默认缩放。
- PUA 字符风格改为默认；重绘部分植物与材料字形，改善轮廓区分、黏连、悬浮图案和可读性。
- 图像地图中的气体按三档浓度显示不同点阵密度，保留上方位置；液体使用自身字形与浓度线条，在双字宽瓦片底部平铺，减少与其他图层的遮挡。
- 清理部分墙体及异象消失后残留的无效色线。修复左右面板 emoji、PUA 字符裁切、缺字符方框，以及悬浮消息被地图覆盖的问题。
- 更换「环境」标签页图标；事件与 NPC 周围改用稀疏、低亮度的字符动画，减少黄色图标遮挡和发光干扰。

#### 发射与装填

- 整理射击界面分区，发射源使用卡片展示数值；弹匣显示图标、剩余弹药与可用总量，并提供可点击的手动装填入口。
- 发射沿用上次选择的来源，无需每次重新选择。弹匣耗尽后，下次瞄准默认尝试花费回合装填，提示装填完成后再次瞄准即可继续发射；消耗型发射物耗尽后按顺序切换到下一个。
- R 在没有空弹匣武器时打开发射源选择；只有发射源选择或射击界面打开且存在可装填弹匣时，才尝试装填。
- 右侧篡改页增加确认与取消入口，沿用预览、确认、支付代价的提交流程。

#### 稳定性与性能

- 修复贴身攻击异象后移动可能引发的闪退，补充运行期错误记录与相关回归检查。
- 优化地图移动与自动行走：减少重复字体校验、视野射线和视距计算，缓存帧内地形字形与可复用的隐藏/记忆地图格，减少无变化区域的重绘。
- 缓存重复日志排版，减少植物照明查询与原生图形解码、传输中的重复复制；保持回合结算、可见信息和默认画质规则。
- 本机真实 WezTerm 的固定 24 步对照样本中，动作结算加刷新中位耗时从 44.501 ms 降至 36.173 ms。此数值不是显示帧率或所有场景的性能保证；详细测量记录保留在开发仓库，不在本仓库重复分发。
- 修复英文模式资源条起点错位、旧存档植物空值导致回合中断、图像层首次初始化错误，以及容器盛装/倒出后右栏跳回默认页的问题。
- 补记调整：少量清水喷雾为 3 单位、消耗 3 想象力，双胞胎吹风机仍为 6。
- 更新回归检查与探针兼容性：Python 3.11 探针关闭可能引起解释器崩溃的分配采样，平台专属用例按平台跳过，并同步字形和滚动视窗断言。

#### 其他改进

- QoL 与键鼠可达性整改：Alt 修饰键全面替代 Ctrl（终端兼容）、统一瞄准事务、底部单行 UI、响应式侧栏。
- 数值混乱化调优：地板/技能/蔓延/心理分档四组再平衡，跨档失控横幅。
- 环境反应表第四批：液体/气体反应全覆盖。

#### 网页端

- 网页端的图像地图、界面布局、篡改操作、图鉴和字体同步改动单独记录于 [Web 0.1.1 更新日志](docs/web-0.1.1-changelog.zh-CN.md)。

### [0.1.0] - 2026-10-28

首个公开试玩版本。**版本号序列从本版重新开始**：内部开发阶段用过的 `0.9.0`
不再代表任何发行版本，已废弃；下方条目仅作历史记录保留。

#### 说明

- 发行包三系统各中英两版：Windows x86_64、Linux x86_64、macOS（Apple Silicon），
  均随包便携 WezTerm 与全部字体，解压即玩、离线运行。
- 包根随附许可材料：`LICENSE`、`LICENSING.md`、`THIRD-PARTY-NOTICES.md`、
  `assets/CREDITS.md`、`assets/licenses/`；字体来源与自带许可在 `assets/fonts/`。
- 字体许可复核：`DreamStrataUnified-Regular.ttf`（OFL-1.1 + MIT + Apache-2.0 + CC-BY-3.0
  物理合并）完成逐源核对后放行，证据见 `assets/fonts/UNIFIED-LICENSE-NOTICE.md`。
- 版本号落到可执行文件与包清单：exe 属性页、`release-manifest.json`、
  macOS `Info.plist`（`CFBundleShortVersionString`）均为 `0.1.0`。

### [0.9.0] - 2026-10-15（内部开发阶段基线，版本号已废弃）

内部开发阶段基线（不对应任何公开版本）。

#### 新增

- **梦层核心循环**：回合制 roguelike 主循环——心智/清醒/想象力三轴心理数值、征兆（状态效果）体系、现实洞察（能力）体系、崩解度与跨层行程
- **环境模拟**：气体扩散与消散、液体流动与反应、地板/墙体材料属性、火/电/爆环境灾害、环境反应配方表（液体 55/55、气体 42/42 覆盖）
- **两谷位面**：图书馆与医院两层梦中梦（位面内守门、专属材料与异象）；千禧园主题层
- **异象生态**：40+ 失控意识（AI、技能、战利品），主动技能开发表驱动（xlsx 内容源）
- **调音系统**：位置语义装备（12 功能词）、联想盘四槽位（补语/修饰/条件/载体）、图案重写
- **篡改系统**：可编辑梦境现实的篡改面板、混乱度与余量结算、按键可重绑
- **任务与委托**：世界账本委托日志（领取/交付/放弃）
- **音频**：全部原创本地合成的音乐与音效（见 `assets/CREDITS.md`）
- **图形**：ASCII/字形渲染、画面特效目录、扫描线与衬线终端配置
- **工程**：PyInstaller 一键打包（`python build.py`）、崩溃报告目录、玩家配置文件（`game_config.ini`）、双语界面（中文/English）

#### 说明

- 测试套件本地维护，不随仓库发布（见 CONTRIBUTING.md「关于测试」）
- CI 提供字节码编译检查与无头冒烟（世界生成 → 渲染一帧 → 存档）

[Unreleased]: https://github.com/dis5mZl1e/oneirscript/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/dis5mZl1e/oneirscript/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dis5mZl1e/oneirscript/releases/tag/v0.1.0

[返回顶部 / Back to top](#zh) · [English](#en)

---

<a id="en"></a>

## English

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers follow [Semantic Versioning](https://semver.org/). The detailed commit history is maintained in the development repository; this repository keeps the public source baseline and release documentation.

### [Unreleased]

No unreleased changes; the 0.1.1 entries below shipped in the release.

### [0.1.1] - 2026-11-01

This update improves desktop map responsiveness, inventory and combat controls, and adds a short introduction for new saves.
0.1.1 was packaged on 2026-11-01: eight desktop packages (Windows / Linux / macOS Apple Silicon and Intel, Chinese and English), a corresponding source archive and checksums. The main branch source is synchronized to this version from development snapshot `d553842a`; see the [v0.1.1 Release](https://github.com/dis5mZl1e/oneirscript/releases/tag/v0.1.1).

#### Introduction and help

- New regular saves open a six-page introduction covering the game, arrow-key/numpad movement, WASD and `/` panel controls, travel without stairs, sentence equipment, tampering and combat. It explains N to descend, B to ascend, and the requirement of 100 dissolution before descending.
- Read or dismiss the introduction without spending a turn. It does not appear in the playable tutorial or automatically return when loading or retrying. Reopen it from Settings → Data → Entering the Dream. Complete Chinese and English text is included.
- Both tamper editors provide a gameplay guide covering targets, words, conditions, scope, costs, chaos, risks and exiting. The guide reuses the association board's information window; reading or closing it does not submit an edit.

#### Inventory and builds

- Inventory defaults to five square slots per row and extends as capacity grows. The old vertical list remains available through the title-bar control, Enter, or `-` / `=` while controlling the right inventory region.
- Slot backgrounds represent item categories, with thin rarity borders. Refine the wooden selection frame, darken corner mounts and retain subtle creases. Add inventory border and icon style settings.
- Typeset large icons directly from font outlines at their final size, following the PUA/common character setting. Move transparent quantity labels to the lower right and enlarge the upper-right equipped star. Place item details above the grid and clarify the name, quantity and collapsible description.
- Fix grid scrolling, left-click use, border alignment, quantity/icon overlap and missing equipment markers. Using an item keeps the inventory open.
- Fix large icons and creased frames reverting after opening windows, switching pages or compressing sidebar text. Retry and recreate graphics layers after transient failures.
- Give construct categories distinct card backgrounds and explain their types and effects in the details. Clicking a card selects it; only its Cast button or Enter activates it.
- Add a Return to Memory link at the top of linked details, returning home from any depth. Improve association-board column syntax visibility, replace catalog placeholders with descriptions, and shorten selected item names with matching English updates.

#### Map, glyphs and feedback

- Add desktop top-bar map zoom and full-map controls, supporting clicks and `(` / `)`. Include 125% and 150% zoom while preserving the existing default scale.
- Make PUA the default character style. Redraw selected plant and material glyphs to improve distinct silhouettes, joined details and readability, and remove detached shapes.
- Render three gas concentration levels with distinct dot densities in the upper tile area. Use each liquid's own glyph and concentration lines along the bottom of double-width tiles, reducing overlap with other layers.
- Remove stray color lines beneath some walls and after anomalies disappear. Fix clipped emoji/PUA characters, missing-glyph boxes and floating messages covered by the map.
- Replace the Environment tab icon. Use sparse, muted character animations around events and NPCs to reduce oversized yellow markers and glow.

#### Firing and reloading

- Organize the firing screen into sections with source cards and stats. Show magazine icons, remaining ammunition and available totals, with a clickable manual reload control.
- Reuse the previously selected firing source. After a magazine runs empty, the next aim attempt tries to reload at the normal turn cost; aim again after the reload message to fire. Exhausted consumable projectiles advance to the next available source in order.
- R opens source selection when no empty-magazine weapon needs reloading. Reload attempts require an open firing/source-selection screen and a reloadable magazine.
- Add confirm and cancel controls to the right tamper editor, using the existing preview, confirmation and cost-payment flow.

#### Stability and performance

- Fix a crash that could occur while moving after a melee attack against an anomaly, with runtime error reporting and regression coverage.
- Reduce repeated font checks, visibility rays and sight-range calculations during movement and automatic walking. Cache terrain glyphs within a frame and reusable hidden/remembered map cells, and avoid redrawing unchanged regions.
- Cache repeated log layout and reduce plant-light queries and redundant copies during native graphics decoding and transport. Preserve turn settlement, information visibility and default visual quality.
- In a local, fixed 24-move WezTerm comparison, median action-plus-refresh time decreased from 44.501 ms to 36.173 ms. This is neither a display frame rate nor a guarantee for every scene; the detailed measurement notes are kept in the development repository and are not redistributed here.
- Fix misaligned English resource bars, empty plant values interrupting turns in older saves, first-frame image-layer initialization, and the sidebar returning to its default page after container fill/pour actions.
- Record an earlier adjustment: a small clean-water spray uses 3 units and costs 3 imagination; the twin hairdryer remains at 6.
- Update regression and probe compatibility: disable allocation sampling that could crash Python 3.11 probes, skip platform-specific cases where appropriate, and update glyph and scrolling-viewport expectations.

#### Other improvements

- QoL and keyboard/mouse accessibility: Alt replaces Ctrl for terminal compatibility, a unified aiming transaction, a single-line footer and a responsive side panel.
- Rebalancing toward less predictable situations: floor effects, skills, propagation and psychological resource bands, with instability banners when crossing bands.
- Fourth batch of environmental reaction entries, covering all registered liquid and gas types.

#### Web

- Image maps, layout, tampering, catalog and font updates for the web client are recorded separately in the [Web 0.1.1 changelog](docs/web-0.1.1-changelog.en.md).

### [0.1.0] - 2026-10-28

First public playable release. **The version sequence restarts here**: the `0.9.0`
used during internal development no longer denotes any release and is deprecated;
the entries below are kept for historical reference only.

#### Notes

- Three platforms, each in Chinese and English: Windows x86_64, Linux x86_64, and
  macOS (Apple Silicon). Every package ships the portable terminal and all fonts, and
  runs offline after extraction.
- License materials ship at the package root: `LICENSE`, `LICENSING.md`,
  `THIRD-PARTY-NOTICES.md`, `assets/CREDITS.md`, and `assets/licenses/`; font
  provenance and their own licenses are in `assets/fonts/`.
- Font review: `DreamStrataUnified-Regular.ttf` (a physical merge of OFL-1.1, MIT,
  Apache-2.0, and CC-BY-3.0 content) is approved for distribution after a per-source
  review; evidence in `assets/fonts/UNIFIED-LICENSE-NOTICE.md`.
- The version is embedded in the shipped artifacts: the Windows executable's version
  resource, `release-manifest.json`, and the macOS `Info.plist`
  (`CFBundleShortVersionString`) all report `0.1.0`.

### [0.9.0] - 2026-10-15 (deprecated internal development baseline)

Baseline prepared during internal development; it is not a published version. This historical baseline entry does not by itself indicate that an official public release or download is available; consult the project README for current availability.

#### Added

- **Core game loop:** a turn-based roguelike with mind, lucidity, and imagination; portents (status effects); insights (abilities); dissolution; and travel between layers.
- **Environmental simulation:** gas diffusion and dissipation, liquid flow and reactions, floor and wall material properties, fire/electric/explosion hazards, and environmental recipes (the recorded baseline covers 55/55 liquid and 42/42 gas entries).
- **Side realms:** the library and hospital, each a two-layer dream within a dream with gates, exclusive materials, and anomalies; a Millennium Garden-themed layer.
- **Anomaly ecology:** more than 40 stray consciousness types with AI, skills, and loot, with active skills driven by the development spreadsheet content source.
- **Attunement system:** position-sensitive equipment with 12 function words, a four-slot association board (complement, modifier, condition, and carrier), and pattern rewriting.
- **Tampering:** an editor for rewriting dream reality, chaos and remaining-capacity settlement, and rebindable controls.
- **Quests and commissions:** a world-ledger quest log supporting acceptance, delivery, and abandonment.
- **Audio:** original, locally synthesized music and sound effects; see `assets/CREDITS.md`.
- **Graphics:** ASCII/glyph rendering, a visual-effects catalog, scanlines, and serif terminal configuration.
- **Engineering:** one-command PyInstaller packaging (`python build.py`), a crash-report directory, player configuration (`game_config.ini`), and Chinese/English interfaces.

#### Notes

- The full test suite is maintained locally and is not published with the repository; see the testing section of CONTRIBUTING.md.
- Public CI provides bytecode compilation and a headless smoke check: world generation, one-frame rendering, and saving.

The counts and feature descriptions above belong to the recorded baseline, rather than a continuously updated inventory of the current game.

[Back to top](#en) · [简体中文](#zh)
