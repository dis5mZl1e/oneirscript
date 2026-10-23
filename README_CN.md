# 梦层 / Oneirscript

> 在梦里，文字可以被篡改，环境可以被利用，离开的路需要自己找到。

**单人 · 回合制 · 程序生成 · 终端游戏 · Python**

简体中文 · [English](README_EN.md) · [项目首页](README.md)

<a id="zh"></a>

**目录**

- [游戏简介](#zh-overview)
- [核心玩法](#zh-features)
- [下载](#zh-download)
- [开始游玩](#zh-play)
- [从源码运行](#zh-source)
- [反馈与参与](#zh-contribute)
- [开源许可](#zh-license)

<a id="zh-overview"></a>

## 游戏简介

**《梦层》是一款以潜意识为舞台的传统 Roguelike。** 你从「梦的起始」醒来，穿过不断变化的梦境，面对游荡的异象、散落的记忆和可以被改写的现实，寻找更深处的核心执念。

每次行动都会改变局势：穿过一片液体、制造一声响动、改动一句描述，都可能打开新的路径，也可能带来意料之外的后果。战斗、观察、环境互动与文字系统共同决定你的选择。

游戏仍在持续开发和调整。当前以终端为主要载体，使用 Python 与 Textual 构建，提供中文和英文界面。

[返回目录](#zh) · [English](README_EN.md#en-overview)

<a id="zh-features"></a>

## 核心玩法

| 玩法 | 你可以做什么 |
|---|---|
| **探索梦境** | 穿过程序生成的房间、洞穴、走廊与迷宫，寻找异常地点，进入拥有独立内容的「梦中梦」。 |
| **篡改现实** | 从环境或对话的描述入手，选择字词与条件，预览修改后的句子，再承担改写带来的费用与风险。 |
| **学习构想** | 寻找并学习具体能力，用它们处理战斗、探索和环境中的特殊局面。 |
| **利用环境** | 让液体、气体、火焰、电场与材料反应参与战术，改变局部环境和通路。 |
| **构筑自身** | 组合装备盘上的词条，配置记忆碎片，学习洞察，在资源与适应能力之间取舍。 |
| **判断与行动** | 观察目标和周围环境，选择近战、远程、投掷或撤离；回合制让你有时间思考下一步。 |

心智、清醒度与想象力各有用途；征兆、噪音和混乱也会影响局面。物品、NPC、事件、图鉴与旧梦记录贯穿探索过程。

[返回目录](#zh) · [English](README_EN.md#en-features)

<a id="zh-download"></a>

## 下载

**下载入口预留，链接将在正式发布时补充。**

| 平台 | 下载链接 |
|---|---|
| Windows | 待发布 |
| macOS | 待发布 |
| Linux | 待发布 |

<!-- 发布时在上表补充经过验证的发行包链接；目前不填写 URL。 -->

请以实际发布的平台、架构和版本说明为准。完整便携发行包将提供游戏所需的终端与字体；从源码运行的方法见下方。

[返回目录](#zh) · [English](README_EN.md#en-download)

<a id="zh-play"></a>

## 开始游玩

1. 下载对应平台的完整发行包，解压整个目录，保留随附的 `assets` 与 `vendor` 等资源。
2. 使用包内的游戏启动入口。游戏优先使用随包 WezTerm 及专用字体配置；也保留其他终端的兼容启动方式。
3. 开始新游戏，从 0 层教学熟悉观察、行动和环境互动，再逐步探索其他系统。

**推荐使用随包 WezTerm。** 它负责游戏的字体与图像地图显示，专用窗口配置与个人全局配置分开。其他终端可以使用字符地图，但字体、颜色和鼠标表现会受终端能力影响。

| 常用操作 | 键位 |
|---|---|
| 移动 | 方向键 / `WASD` |
| 等待 | `.` |
| 拾取 | `G` |
| 打开或关闭完整键位表 | `Alt+H`，或点击右侧面板的键位表入口 |
| 展开或收起底栏 | `Alt+Z`，或点击底栏展开按钮 |

具体界面的操作以游戏内提示和完整键位表为准。界面语言、音量及显示选项可在设置中调整。更新游戏前请备份存档。

[返回目录](#zh) · [English](README_EN.md#en-play)

<a id="zh-source"></a>

## 从源码运行

需要 **Python 3.11 或更新版本**。取得源码后，在项目根目录运行；以下方式使用独立虚拟环境，无需修改系统 Python。

**Windows（PowerShell）**

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

需要留在当前终端时，在运行命令末尾添加 `--compat-terminal`。源码依赖的安装需要网络；源码目录不一定包含对应平台的便携终端。

开发者可用以下命令执行不进入交互界面的冒烟检查，并将测试存档写入单独目录：

```bash
python run_demo.py --smoke --save-dir save-smoke
```

Windows 本机打包入口保留在原开发仓库的 [build.py](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/build.py)。开发环境与贡献约定见 [CONTRIBUTING.md](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/CONTRIBUTING.md)。

[返回目录](#zh) · [English](README_EN.md#en-source)

<a id="zh-contribute"></a>

## 反馈与参与

欢迎反馈问题、分享游玩体验，以及参与翻译、内容创作和程序改进。可以使用所在代码托管平台的问题区与合并请求功能。

报告问题时，请尽量附上：游戏版本、系统与终端、复现步骤、预期与实际结果；有截图或报错日志时一并提供。分享存档和日志前，请先检查其中是否包含个人信息。

- [贡献指南](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/CONTRIBUTING.md)：开发约定与提交说明。
- [行为准则](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/CODE_OF_CONDUCT.md)：社区参与规范。
- [安全策略](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/SECURITY.md)：安全问题的报告方式；请勿在公开问题区披露漏洞细节。
- [更新记录](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/CHANGELOG.md)：已记录的版本变化。

完整测试套件与开发工具保留在原开发仓库，不包含在本精简仓库中；贡献的验证方式见贡献指南。

[返回目录](#zh) · [English](README_EN.md#en-contribute)

<a id="zh-license"></a>

## 开源许可

**项目自有代码采用 [GNU GPLv3（GPL-3.0-only）](LICENSE)。** 允许商业使用、修改和分发；分发受许可覆盖的程序与修改版时，需要遵守 GPLv3 的对应源码等要求。

字体、图标、原创音频、WezTerm 及其他第三方组件分别适用其独立许可，不统一改为 GPL。完整范围见 [LICENSING.md](LICENSING.md)，来源与声明见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。

Copyright (c) 2026 dis5mZl1e。项目名称、标识与官方身份的使用，不因代码许可自动获得背书。

[返回目录](#zh) · [English](README_EN.md#en-license)
