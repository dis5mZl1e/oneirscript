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

`DreamStrataUnified-Regular.ttf` 是物理合并字体，**2026-10-27 复核后可以随发行包分发**。
合并来源为 OFL-1.1（Noto Serif SC／Symbols(2)／Math／Serif 系列、Victor Mono 与 Noto Emoji 轮廓）、
MIT（Phosphor 派生 Interface Icons）、Apache-2.0（Material Design Icons 派生 Material Icons）与
CC-BY-3.0（Game-icons.net 派生 Dream Icons）；四种许可都允许合并与再分发，
且上游许可文本与 14 个上游字体名称表**均未声明保留字体名（Reserved Font Name）**，
产物已整体改名为 Dream Strata 系列。合并字体整体以 OFL-1.1 分发，其中嵌入的
MIT／Apache-2.0／CC-BY-3.0 轮廓各自保留原许可与署名；OFL 全文、上游版权声明、
NOTICE-MDI、逐项 Game-icons 署名与修改说明均随字体目录分发。
逐源哈希、cmap 并集与复核命令见 `assets/fonts/UNIFIED-LICENSE-NOTICE.md`
（工程与许可条款判断，不替代法务意见）。

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

`DreamStrataUnified-Regular.ttf` is a physically merged font that, after the 2026-10-27 review, **may be distributed with the release packages**. Its sources are OFL-1.1 (Noto Serif SC / Symbols (2) / Math / Serif families, Victor Mono, and Noto Emoji outlines), MIT (Phosphor-derived Interface Icons), Apache-2.0 (Material Design Icons-derived Material Icons), and CC-BY-3.0 (Game-icons.net-derived Dream Icons). All four licenses permit merging and redistribution, and neither the bundled OFL texts nor the name tables of the 14 upstream fonts declare a Reserved Font Name; the merged font has been renamed throughout to the Dream Strata family. The merged font as a whole is distributed under OFL-1.1, while the embedded MIT / Apache-2.0 / CC-BY-3.0 outlines retain their own licenses and notices. The OFL text, upstream copyright notices, NOTICE-MDI, the per-icon Game-icons attribution, and the modification statement ship with the font directory. Per-source hashes, the cmap union, and the review commands are recorded in `assets/fonts/UNIFIED-LICENSE-NOTICE.md` (an engineering and license-terms assessment, not legal advice).

### Branding and provenance

The code license does not automatically authorize presenting a derivative as an official release or claiming endorsement by the author. Rules for using the Oneirscript / 梦层 name and logo should be maintained separately from the code license. This document does not claim that a trademark has been registered, nor does it impose a branding policy as an additional restriction on rights granted by the GPL. Preserve accurate copyright notices, provenance, third-party attribution, and modification information.

### Before the first public release

This change is not a complete legal certification of contributor ownership or every binary resource. Continue checking code provenance, font copyrights, icon sources, and bundled DLLs, and provide source corresponding to the distributed binaries. Replacing the root license with the GPL does not by itself establish compliance for an existing package. The internal checklist is recorded in `docs/261022开源许可与第三方资源核查.md`.

If an earlier copy was lawfully licensed to someone under previous terms, this change does not revoke their existing rights. Keep the Git history; rewriting or force-pushing it is not required to change the license.

This English text explains the project's licensing boundaries. It does not amend the standard license texts or grant rights beyond the applicable licenses.

[Back to top](#en) · [简体中文](#zh)
