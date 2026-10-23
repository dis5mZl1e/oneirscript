# 第三方组件声明 / Third-Party Notices

[简体中文](#zh) · [English](#en)

<a id="zh"></a>

## 简体中文

2026-10-22 核查。项目自有代码采用 GPL-3.0-only，第三方组件仍归各自权利人所有，
保留各自许可、版权和 NOTICE。以下版本来自本机实际安装环境，不是跨平台发行锁文件，
也不证明旧 EXE 已使用这些版本。许可全文须随实际发行内容交付，不能用本表或 URL 替代。

### Python 直接依赖与构建工具

| 组件 | 本机版本 | 许可及备注 |
|---|---|---|
| [Rich](https://github.com/Textualize/rich) | 14.3.3 | MIT |
| [Textual](https://github.com/Textualize/textual) | 0.89.1 | MIT |
| [NumPy](https://github.com/numpy/numpy) | 2.4.6 | 主体 BSD-3-Clause；当前元数据另列 0BSD、MIT、Zlib、CC0-1.0；wheel 的数学运行库另核 |
| [asciimatics](https://github.com/peterbrittain/asciimatics) | 1.15.0 | Apache-2.0 |
| [pygame](https://github.com/pygame/pygame/tree/2.6.1) | 2.6.1 | LGPL；上游提供 LGPL-2.1 正文，随 wheel 的 SDL 与编解码库另核 |
| [openpyxl](https://foss.heptapod.net/openpyxl/openpyxl) | 3.1.5 | MIT |
| [Pillow](https://github.com/python-pillow/Pillow) | 12.2.0 | MIT-CMU；图像库二进制另核 |
| [fontTools](https://github.com/fonttools/fonttools) | 4.67.0 | MIT，并保留 LICENSE.external |
| [PyInstaller](https://github.com/pyinstaller/pyinstaller) | 6.22.2 | GPL-2.0-or-later，带 bootloader exception；运行时 hooks 为 Apache-2.0，须保留完整 COPYING |

上述主体许可未发现必须更换依赖才能采用 GPLv3 的障碍；这不是对所有随包 DLL
和嵌入代码的完整兼容性认证。打包工具例外不会豁免游戏自身的 GPLv3 义务。

当前依赖闭包还包括：markdown-it-py 4.0.0、mdurl 0.1.2、platformdirs 4.11.7、
pyfiglet 1.0.4、wcwidth 0.6.0、et_xmlfile 2.0.0（主体 MIT）；Pygments 2.19.2
（BSD-2-Clause）；typing_extensions 4.15.0（PSF-2.0）；Windows 的 pywin32 311
（各模块许可须分别保留，不笼统替换为 GPL）。pyfiglet 的附带字库亦需核对实际使用。

构建链还包括 altgraph、packaging、pefile、pyinstaller-hooks-contrib、pywin32-ctypes、
setuptools；构建工具的完整依赖闭包并不等于全部都会进入游戏二进制。
Python 解释器及随附的第三方代码必须保留实际 Python 版本的完整 LICENSE。

### 字体与图标

| 内容 | 独立许可 | 随包材料 |
|---|---|---|
| Noto Serif SC、Victor Mono、Noto Symbols / Symbols 2、Math 及辅助文字字体衍生阅读字体 | OFL-1.1 | assets/fonts/OFL.txt、UPSTREAM-COPYRIGHTS.txt、LICENSES.md |
| Noto Emoji 衍生地图轮廓字体 | OFL-1.1 | NotoEmoji-OFL.txt、glyph-manifest.json |
| Noto Color Emoji 千禧园子集 | OFL-1.1 | NotoColorEmoji-OFL.txt、emoji-package.json |
| Phosphor 衍生 Interface Icons | MIT | LICENSE-Phosphor-MIT.txt |
| Material Design Icons 衍生 Material Icons | Apache-2.0 | LICENSE-MDI-Apache-2.0.txt、NOTICE-MDI.txt |
| Game-icons 衍生 Dream Icons | CC-BY-3.0 | LICENSE-GameIcons-CC-BY-3.0.txt、逐项 ATTRIBUTION-GameIcons.md |

OFL 字体随游戏聚合发行，不要求把程序改为 OFL，也不能将字体统一改为 GPL。
独立图标资产不会仅因被游戏加载就变为 GPL 代码；嵌入或物理合并仍须另核。
Game-icons 的作者、来源、许可与 PUA 重映射／规范化说明应继续保留。

**统一字体候选尚未放行**：`DreamStrataUnified-Regular.ttf` 物理合并了多种许可来源。
必须先处理整体字体的许可兼容性，不能因名称叫“混合字体”就视作独立资源聚合。
当前文件存在且打包会复制它；不是默认字体不代表已经排除分发。

### WezTerm 与平台组件

随包 WezTerm 版本标识为 `20240203-110809-5046fc22`，主体 MIT。
许可见 `vendor/wezterm/LICENSE.md` 与 `assets/licenses/WezTerm-LICENSE.md`。
其内置 JetBrains Mono、Noto Color Emoji、Roboto、Symbols Nerd Font Mono 的授权
不能由游戏自己的字体声明替代，须保留该版本实际使用的字体声明。

本机目录还含 Mesa、libEGL.dll、libGLESv2.dll、conpty.dll、OpenConsole.exe 等，
目前只发现顶层 WezTerm LICENSE.md，尚未完成这些独立组件的版本、来源和许可核查。
不得将整个目录笼统声明为 MIT，也不得擅自按网上其他版本的许可认定本机 DLL。

### 音频与其他图像

原创合成音频继续按 `assets/licenses/Original-Audio-MIT.txt` 分发，见 `assets/CREDITS.md`。
新增代码许可不改变这项已有独立许可。
图标源图 `assets/icon_src.jpg`、`assets/icon.ico` 及加载／终端纹理仍需保存可核对的
创作来源；本声明不凭文件位于仓库中就将来源不明的图像认定为原创。

### 二进制分发尚需完成

- 对实际 EXE、wheel 和终端目录形成版本、哈希、许可证及版权清单，补齐离线全文。
- 保存 pygame/SDL 等适用 LGPL 组件的对应源码与所需重建／替换材料；
  不能仅以“动态链接、未修改”认定所有义务已履行。
- 提供与发行版对应的 GPL 源码及构建脚本，依法选择源码交付方式。
- 将 LICENSE、LICENSING.md、本声明及资源许可一起纳入所有平台的发行包。

详情与证据见 [本次核查记录](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/docs/261022开源许可与第三方资源核查.md)。

[返回顶部 / Back to top](#zh) · [English](#en)

---

<a id="en"></a>

## English

Reviewed on 2026-10-22. Project-owned code uses GPL-3.0-only. Third-party components remain the property of their respective copyright holders and retain their licenses, copyrights, and NOTICE files. The versions below are from the actual local installation; this is not a cross-platform release lockfile, nor evidence that an older EXE contains these versions. Distributions must include the required complete license materials for their actual contents. This table and upstream URLs are not substitutes.

### Direct Python dependencies and build tools

| Component | Installed version | License and notes |
|---|---|---|
| [Rich](https://github.com/Textualize/rich) | 14.3.3 | MIT |
| [Textual](https://github.com/Textualize/textual) | 0.89.1 | MIT |
| [NumPy](https://github.com/numpy/numpy) | 2.4.6 | Primarily BSD-3-Clause; current metadata also lists 0BSD, MIT, Zlib, and CC0-1.0. Native math libraries in the wheel require separate review. |
| [asciimatics](https://github.com/peterbrittain/asciimatics) | 1.15.0 | Apache-2.0 |
| [pygame](https://github.com/pygame/pygame/tree/2.6.1) | 2.6.1 | LGPL; upstream supplies the LGPL-2.1 text. SDL and codec libraries in the wheel require separate review. |
| [openpyxl](https://foss.heptapod.net/openpyxl/openpyxl) | 3.1.5 | MIT |
| [Pillow](https://github.com/python-pillow/Pillow) | 12.2.0 | MIT-CMU; native image libraries require separate review. |
| [fontTools](https://github.com/fonttools/fonttools) | 4.67.0 | MIT; also retain LICENSE.external. |
| [PyInstaller](https://github.com/pyinstaller/pyinstaller) | 6.22.2 | GPL-2.0-or-later with the bootloader exception; runtime hooks are Apache-2.0. Retain the complete COPYING file. |

No primary-license obstacle requiring replacement of the dependencies above was identified for adopting GPLv3. This is not a complete compatibility certification of all bundled DLLs or embedded code. The packaging tool's exception does not waive the game's own GPLv3 obligations.

The current dependency closure also includes markdown-it-py 4.0.0, mdurl 0.1.2, platformdirs 4.11.7, pyfiglet 1.0.4, wcwidth 0.6.0, and et_xmlfile 2.0.0 (primarily MIT); Pygments 2.19.2 (BSD-2-Clause); typing_extensions 4.15.0 (PSF-2.0); and pywin32 311 on Windows. Retain the applicable module licenses for pywin32 rather than relabeling all of it GPL. Check the actual font resources used from pyfiglet separately.

The build chain also includes altgraph, packaging, pefile, pyinstaller-hooks-contrib, pywin32-ctypes, and setuptools. A build tool's installed dependency closure is not the same as the contents of a game executable. Retain the complete LICENSE for the actual Python version, including its bundled third-party notices.

### Fonts and icons

| Content | Separate license | Bundled materials |
|---|---|---|
| Reading fonts derived from Noto Serif SC, Victor Mono, Noto Symbols / Symbols 2, Math, and supplementary script fonts | OFL-1.1 | assets/fonts/OFL.txt, UPSTREAM-COPYRIGHTS.txt, LICENSES.md |
| Map outline fonts derived from Noto Emoji | OFL-1.1 | NotoEmoji-OFL.txt, glyph-manifest.json |
| Millennium Garden subset of Noto Color Emoji | OFL-1.1 | NotoColorEmoji-OFL.txt, emoji-package.json |
| Phosphor-derived Interface Icons | MIT | LICENSE-Phosphor-MIT.txt |
| Material Design Icons-derived Material Icons | Apache-2.0 | LICENSE-MDI-Apache-2.0.txt, NOTICE-MDI.txt |
| Game-icons-derived Dream Icons | CC-BY-3.0 | LICENSE-GameIcons-CC-BY-3.0.txt and per-icon ATTRIBUTION-GameIcons.md |

Aggregating OFL fonts with the game does not require licensing the program under the OFL, nor does it permit relicensing the fonts collectively under the GPL. Loading separately distributed icon assets does not by itself turn them into GPL code; embedding or physical merging requires separate review. Retain Game-icons author credits, sources, licenses, and the PUA remapping/normalization notices.

**The unified font candidate is not approved for distribution.** `DreamStrataUnified-Regular.ttf` physically combines content under multiple licenses. Resolve the licensing compatibility of the combined font first; calling it a mixed font does not make it an aggregation of separate resources. The file exists and current packaging copies it. Being non-default does not establish that it is excluded from distribution.

### WezTerm and platform components

The bundled WezTerm version identifier is `20240203-110809-5046fc22`; WezTerm itself is MIT-licensed. See `vendor/wezterm/LICENSE.md` and `assets/licenses/WezTerm-LICENSE.md`. Its embedded JetBrains Mono, Noto Color Emoji, Roboto, and Symbols Nerd Font Mono need their own applicable notices. The game's font notices do not replace notices for these embedded fonts.

The local terminal directory also contains Mesa, libEGL.dll, libGLESv2.dll, conpty.dll, OpenConsole.exe, and other components. Only the top-level WezTerm LICENSE.md was found; the separate components' versions, provenance, and licenses have not been fully reviewed. Do not label the entire directory MIT, or assume that licensing information for a different online version describes these local DLLs.

### Audio and other images

Original synthesized audio retains the MIT license in `assets/licenses/Original-Audio-MIT.txt`; see `assets/CREDITS.md`. Changing the code license does not change that separate license. Retain verifiable creation records for `assets/icon_src.jpg`, `assets/icon.ico`, and loading/terminal textures. A file's presence in the repository is not evidence that an image of unknown provenance is original.

### Remaining binary-distribution work

- Inventory the actual EXE, wheels, and terminal directory with versions, hashes, licenses, and copyright notices, and supply the complete required license texts offline.
- Preserve Corresponding Source and required rebuild/replacement materials for applicable LGPL components such as pygame/SDL. Describing them as dynamically linked and unmodified does not by itself demonstrate compliance with every obligation.
- Supply GPL source and build scripts corresponding to each release, using a compliant source-delivery method.
- Include LICENSE, LICENSING.md, this notice, and the complete resource licensing materials in distributions for every platform.

Details and evidence are recorded in the [internal review](https://github.com/dis5mZl1e/dream-strata/blob/b88331f963fcfc41ef93c41441dfe483460ca4d1/docs/261022开源许可与第三方资源核查.md).

[Back to top](#en) · [简体中文](#zh)


本仓库为精简的源码运行版本，不包含 WezTerm 二进制、构建工具、开发文档或统一字体研究候选。历史开发记录与构建材料保留在原开发仓库。

This repository contains the source-playable edition. WezTerm binaries, build tools, development documents, and the unified-font research candidate are excluded. Historical development records and build materials remain in the original development repository.
