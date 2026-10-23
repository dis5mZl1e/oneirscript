# 梦层许可边界 / Licensing

[简体中文](#zh) · [English](#en)

<a id="zh"></a>

## 简体中文

2026-10-22，正式公开发布前调整。Copyright (c) 2026 dis5mZl1e。

### 自有代码

除文件或目录中另有明确声明外，本项目自有程序代码、构建和启动脚本、
与程序一同维护的自有规则数据和文档采用 **GNU General Public License,
version 3 only**（SPDX：`GPL-3.0-only`）。完整且未经修改的许可证见 `LICENSE`。
这不包含第三方代码和下述单独授权的资源，也不表示将他人的版权转归本项目。

本程序为自由软件，可以按 GNU GPL 第 3 版重新分发和修改；不提供任何担保，
包括适销性和适用于特定用途的默示担保。具体权利、义务以 `LICENSE` 为准。

商业使用、收费分发及合法衍生开发均被允许。分发受 GPL 覆盖的二进制时，
应按 GPLv3 第 6 条提供对应源码的合规取得方式；源码包括修改所需的优选形式、
相关规则数据、必要构建与安装脚本，不能只提供一份与发行版本无关的仓库链接。
仅私人修改不会自动产生向公众发布源码的义务。

这里选择 `GPL-3.0-only`，没有自动授权采用未来版本。后续若要扩展至
`GPL-3.0-or-later`，应再核对权利人与贡献者授权。

### 单独授权的资源

| 路径／内容 | 适用许可 | 声明位置 |
|---|---|---|
| `assets/fonts` 中 Noto、Victor Mono 衍生阅读字体、地图图标字体与彩色 emoji 子集 | OFL-1.1 | `assets/fonts/LICENSES.md`、各 OFL 文本及版权声明 |
| `DreamStrataInterfaceIcons.ttf`，Phosphor 衍生子集 | MIT | `assets/fonts/LICENSE-Phosphor-MIT.txt` |
| `DreamStrataMaterialIcons.ttf`，MDI 衍生子集 | Apache-2.0 | `assets/fonts/LICENSE-MDI-Apache-2.0.txt`、`NOTICE-MDI.txt` |
| `DreamStrataDreamIcons.ttf`，Game-icons 衍生子集 | CC-BY-3.0 | `assets/fonts/LICENSE-GameIcons-CC-BY-3.0.txt`、`ATTRIBUTION-GameIcons.md` |
| `assets/fonts/ICONS-LICENSE.txt` 明确覆盖的本项目原创图形研究稿 | MIT | 保留原有单独授权；不适用于整个游戏或所有字体 |
| `assets/music`、`assets/sfx` 原创合成音频 | MIT | `assets/licenses/Original-Audio-MIT.txt`、`assets/CREDITS.md` |
| 随包 WezTerm 主体 | MIT | `vendor/wezterm/LICENSE.md`、`assets/licenses/WezTerm-LICENSE.md` |
| Python 依赖、运行时及第三方二进制 | 各上游许可 | `THIRD-PARTY-NOTICES.md` 和实际发行文件的许可材料 |

`.wezterm/fonts` 是字体资源副本，适用对应源字体的许可，不因所在目录变为 GPL。
字体构建工具的代码许可与生成字体的许可是两个问题；运行 GPL 构建工具本身
不会将 OFL 字体或第三方图标改为 GPL。

`DreamStrataUnified-Regular.ttf` 是混合许可的研究候选，**尚未完成物理合并后的
许可兼容性核查，不作为已批准公开分发的字体**。现有构建会复制整个字体目录，
所以“不是默认字体”不等于“不会进入发行包”；首次公开发布前必须修正发行内容，
或完成替换、额外授权与许可复核。不能把它直接声明为 OFL 或 GPL 后放行。

### 品牌和来源

代码许可不自动授予将衍生版宣传为官方版本、声称作者背书的权利。
“梦层 / Oneirscript”及 Logo 的品牌使用规则应与代码许可分开制定；此处不声称
已取得注册商标，也不将品牌政策作为限制 GPL 所授代码权利的附加条件。
版权声明、来源、第三方署名和实际修改情况应如实保留。

### 首次公开发布前

这次调整不是对贡献者权属和所有二进制资源的完整法律认证。应继续核查代码来源、
字体版权、图标来源及随包 DLL，完成与二进制版本对应的源码交付。
现有包尚不能仅凭根目录换成 GPL 就认定全部合规。
具体清单见 `docs/261022开源许可与第三方资源核查.md`。

旧副本如已在此前许可下合法授予他人，本次调整不撤销其已有权利。
保留 Git 历史即可，无须为改许可强推或删除历史。

[返回顶部 / Back to top](#zh) · [English](#en)

---

<a id="en"></a>

## English

### Project-owned code

Updated on 2026-10-22, before the first official public release. Copyright (c) 2026 dis5mZl1e.

Unless a file or directory explicitly states otherwise, this project's own program code, build and launch scripts, rule data maintained with the program, and documentation are licensed under the **GNU General Public License, version 3 only** (SPDX: `GPL-3.0-only`). The complete, unmodified license text is in `LICENSE`. This does not include third-party code or the separately licensed resources below, and does not transfer third-party copyrights to this project.

This program is free software: you may redistribute and modify it under version 3 of the GNU GPL. It comes without any warranty, including implied warranties of merchantability or fitness for a particular purpose. See `LICENSE` for the governing terms.

Commercial use, paid distribution, and lawful derivative development are permitted. When distributing binaries covered by the GPL, provide a compliant means of obtaining the Corresponding Source under GPLv3 section 6. This includes the preferred form for modification, relevant rule data, and necessary build and installation scripts. A generic repository link unrelated to the distributed version is not sufficient. Private modification alone does not automatically require publishing source code to the public.

This project uses `GPL-3.0-only`; it does not automatically authorize future GPL versions. Any later change to `GPL-3.0-or-later` should be checked against the permissions of copyright holders and contributors.

### Separately licensed resources

| Path or content | License | Notice location |
|---|---|---|
| Noto- and Victor Mono-derived reading fonts, map icon fonts, and color emoji subsets in `assets/fonts` | OFL-1.1 | `assets/fonts/LICENSES.md`, the OFL texts, and copyright notices |
| `DreamStrataInterfaceIcons.ttf`, a Phosphor-derived subset | MIT | `assets/fonts/LICENSE-Phosphor-MIT.txt` |
| `DreamStrataMaterialIcons.ttf`, an MDI-derived subset | Apache-2.0 | `assets/fonts/LICENSE-MDI-Apache-2.0.txt` and `NOTICE-MDI.txt` |
| `DreamStrataDreamIcons.ttf`, a Game-icons-derived subset | CC-BY-3.0 | `assets/fonts/LICENSE-GameIcons-CC-BY-3.0.txt` and `ATTRIBUTION-GameIcons.md` |
| Original graphical studies explicitly covered by `assets/fonts/ICONS-LICENSE.txt` | MIT | Their existing separate license is retained; it does not cover the entire game or all fonts |
| Original synthesized audio in `assets/music` and `assets/sfx` | MIT | `assets/licenses/Original-Audio-MIT.txt` and `assets/CREDITS.md` |
| Bundled WezTerm itself | MIT | `vendor/wezterm/LICENSE.md` and `assets/licenses/WezTerm-LICENSE.md` |
| Python dependencies, runtime, and third-party binaries | Their respective upstream licenses | `THIRD-PARTY-NOTICES.md` and the license materials for the actual distributed files |

`.wezterm/fonts` contains copies of font resources. Each copy retains the license of its source font; its directory does not make it GPL-licensed. A font-building tool and the font it produces have separate licensing considerations. Running a GPL-licensed build tool does not by itself relicense OFL fonts or third-party icons under the GPL.

`DreamStrataUnified-Regular.ttf` is a mixed-license research candidate. **The licensing compatibility of its physically merged content has not been fully checked, and it is not approved for public distribution.** Existing build scripts copy the entire font directory: being non-default does not mean the file is excluded from a release. Before public release, correct the distributed contents or complete the necessary replacements, additional permissions, and licensing review. Simply labeling it OFL or GPL is not a resolution.

### Branding and provenance

The code license does not automatically authorize presenting a derivative as an official release or claiming endorsement by the author. Rules for using the Oneirscript / 梦层 name and logo should be maintained separately from the code license. This document does not claim that a trademark has been registered, nor does it impose a branding policy as an additional restriction on rights granted by the GPL. Preserve accurate copyright notices, provenance, third-party attribution, and modification information.

### Before the first public release

This change is not a complete legal certification of contributor ownership or every binary resource. Continue checking code provenance, font copyrights, icon sources, and bundled DLLs, and provide source corresponding to the distributed binaries. Replacing the root license with the GPL does not by itself establish compliance for an existing package. The internal checklist is recorded in `docs/261022开源许可与第三方资源核查.md`.

If an earlier copy was lawfully licensed to someone under previous terms, this change does not revoke their existing rights. Keep the Git history; rewriting or force-pushing it is not required to change the license.

This English text explains the project's licensing boundaries. It does not amend the standard license texts or grant rights beyond the applicable licenses.

[Back to top](#en) · [简体中文](#zh)


本仓库为精简的源码运行版本，不包含 WezTerm 二进制、构建工具、开发文档或统一字体研究候选。历史开发记录与构建材料保留在原开发仓库。

This repository contains the source-playable edition. WezTerm binaries, build tools, development documents, and the unified-font research candidate are excluded. Historical development records and build materials remain in the original development repository.
