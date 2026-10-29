# Dream Strata Serif Mono — 字体授权与来源

内置终端字体 `DreamStrataSerifMono-Regular.ttf` 由以下 SIL Open Font
License 1.1 上游合成（构建脚本：`scripts/build_serif_mono_font.py`）。
按 OFL 要求，本字体已放弃各上游"保留字体名"，以新名
**Dream Strata Serif Mono** 分发；仅作度量归一（等宽化/缩放）与按需取字，
未做其他衍生创作。

| 用途 | 上游 | 授权 | 来源 |
|---|---|---|---|
| CJK 底衬 | Noto Serif SC（思源宋体 SC，Google 全量构建） | OFL 1.1 | fonts.google.com / googlefonts/noto-cjk |
| 拉丁/框线/方块/盲文 | Victor Mono | OFL 1.1 | github.com/VSMajor/victor-mono（经 Google Fonts） |
| 杂项符号 | Noto Sans Symbols / Symbols 2 | OFL 1.1 | notofonts.github.io |
| 数学符号 | Noto Sans Math | OFL 1.1 | notofonts.github.io |
| 冷门脚本（ϟ א ღ ࿐ 圣书体 谚文） | Noto Serif (Greek)/Hebrew/Georgian/Tibetan、Noto Sans Egyptian Hieroglyphs、Noto Serif KR | OFL 1.1 | fonts.google.com |
| emoji 补字（仅 U+1F6E2 🛢） | Noto Emoji（单色轮廓） | OFL 1.1 | github.com/google/fonts/tree/main/ofl/notoemoji（`NotoEmoji-OFL.txt`） |

完整 OFL 1.1 文本见同目录 `OFL.txt`。各上游版权声明另见
`UPSTREAM-COPYRIGHTS.txt`：从实际构建输入的 name 表逐项保留，并记录输入哈希。
来源名称列表不能代替上游版权声明；字体内的单一 nameID 0 也不保证保留全部上游声明。

## 宋体阅读版（当前默认）

`DreamStrataSongReading-Regular.ttf`（Dream Strata Song Reading）由同一 OFL-1.1
混合构建流程生成，中文底衬换为 Noto Serif SC Medium（500），ASCII 使用底衬的
衬线字形并统一到半格，其他符号来源沿用上表。构建入口为
`scripts/build_song_reading_font.py`，上游和产物哈希见 `song-reading.json`。
原版 `DreamStrataSerifMono-Regular.ttf` 保留，便于对照与恢复。

2026-10-22 补字：阅读版额外从 [Google Fonts Noto Emoji](https://github.com/google/fonts/tree/main/ofl/notoemoji)
（Noto Emoji v3.002 可变字体，默认 400 字重，单色轮廓，OFL-1.1，全文
`NotoEmoji-OFL.txt`）并入 **仅 U+1F6E2 🛢 一个码位**，用于思绪容器图标；
不整表合并，不新增上游依赖。字形按 UPM 2048 -> 1000 等比换算后适配
ascent 900 / descent -280，不拉伸；源文件为构建素材 `scripts/_fontsrc/notoemoji.ttf`。
同样的白名单机制（`EXTRA_CPS`，来源回退 `symbols2`）也适用于
`scripts/build_serif_mono_font.py` 的其它变体构建。

## 千禧园彩色 emoji 子集

右栏锁图标使用 `DreamStrataLockOutline.ttf`：从同一 Noto Emoji 单色字体
提取 U+1F512、U+1F513，使用 OFL-1.1，许可全文见 `NotoEmoji-OFL.txt`；
构建脚本为 `scripts/build_lock_outline_font_261027.py`。

混乱专属异象（嗔影/空心者/伪光者）使用 `DreamStrataChaosOutline.ttf`：
与锁图标**同源同流程**——从同一 Noto Emoji 单色可变字体在 wght=400 实例化后
提取 U+1F47F 👿、U+1F5A4 🖤、U+1F607 😇 三个码位，族名
`Dream Strata Chaos Outline`，不含 COLR/CBDT/sbix/SVG 彩色表；使用 OFL-1.1，
许可全文见 `NotoEmoji-OFL.txt`；构建脚本为
`scripts/build_chaos_outline_font_261027.py`。

`DreamStrataMillenniumEmoji.ttf` 从 Noto Color Emoji v2.051 提取 26 个单码位图标，
保留 CBDT/CBLC 彩色位图，去除组合替换，并以新族名 Dream Strata Millennium Emoji 分发。
上游字体版权字段保留，许可为 OFL-1.1，全文见 `NotoColorEmoji-OFL.txt`。
来源、源文件与产物 SHA256、精确码位及符号键记录在 `emoji-package.json`。
其他游戏图标保持原有回退；后续替换须由用户明确指定。

## 专用图标轮廓版（2026-10-17）

用户实测后要求替换像素图标。`DreamStrataIcons.ttf` 2.0 由 Noto Emoji
（450 字重实例）及 Noto Sans Symbols / Symbols 2 的 OFL 轮廓生成，以新族名
Dream Strata Icons 分发，沿用稳定 PUA 槽。地板点亦从 Noto Sans Symbols 2
的圆点轮廓导入，等比缩放并在双列瓦片中心重新定位。
所有导入轮廓等比缩放，不影响正文、千禧园彩色子集或其他回退字符。

上游：[Google Fonts Noto Emoji](https://github.com/google/fonts/tree/main/ofl/notoemoji)，
Google LLC；许可全文 `NotoEmoji-OFL.txt`，符号字体许可全文 `OFL.txt`。
原始 emoji 文件哈希、各槽来源和等比缩放记录见 `glyph-manifest.json`，
构建入口 `scripts/build_game_icon_font.py`。旧 `ICONS-LICENSE.txt` 仅对应保留在
源码 ART 中的原创像素研究稿，不再作为当前字体的发行许可证。

2026-10-25 内容扩展的 E588–E677 图标继续遵循 OFL-1.1。逐码位轮廓来源锁定在
随仓库的 Noto Emoji、Noto Sans Symbols 2、Noto Sans Math、Noto Serif、Noto Serif SC
Medium 与 Noto Sans Egyptian Hieroglyphs 字体；来源文件哈希和 Unicode 码位记录在
`DreamStrataIcons.ttf` 的 `glyph-manifest.json`，每个新增条目也在
`dream_demo/data/expansion/catalog.json` 中声明。上游版权及许可证文本见
`UPSTREAM-COPYRIGHTS.txt`、`OFL.txt` 与 `NotoEmoji-OFL.txt`。


## 地图大轮廓槽（2026-10-18，docs/261018方案合集.md 第 7 节）

`DreamStrataIcons.ttf` 2.3 的 `map:` 前缀地图专用槽（PUA 0xE2C0–0xE33F，72 个，
旧槽位不重排）：

- 轮廓类（34 + 9 异象 + 5 植物）：轮廓取自随包 `DreamStrataSongReading-Regular.ttf`
  中玩家已经认识的原形（OFL-1.1 派生，上游清单见上），由
  `scripts/build_game_icon_font.py` 按类别目标等比放大并居中；不新增上游来源、
  不做非等比拉伸。
- 构件类（15 + 9）：排气口、换气扇/传送带四向、净玻璃隔屏、枕木、吸光苔墙、
  悔恨之锚、共鸣报警器、推书车；以及纸鱼、噩梦牧者、巡回放映队、长镜头导演、
  遗忘档案员、未完成句号、全声合唱的专门构图与气体三档整格纹理，由本项目在
  `dream_demo/data/icon_glyphs.py` 的 `MAP_SHAPES` 以归一化矩形/抖动构图（MIT，
  见 `ICONS-LICENSE.txt`），箭头字形仍取自阅读字体并等比叠放。

每槽的来源字形、类别目标、构图名与缩放记录写在 `glyph-manifest.json` 的
`map_icon` / `map_shape` / `source_family` 字段。旧槽位与普通阅读字形不变。

## 语义图标子集（2026-10-19 首批；2026-10-21 专属补批）

首批 69 个语义图标分成三个受控子集，只含选中轮廓并重映射到 E400–E57F，
不包含上游 ASCII/CJK/品牌或原厂 PUA cmap。

2026-10-21 §16 专属补批新增 84 个征兆字形（U+E448–U+E4A5），同样只打包选中
轮廓：三个子集现在是 50（Interface）/ 30（Material）/ 73（Dream）个字形，
合计 153；Game-icons 的逐项作者与来源页已补全到 `ATTRIBUTION-GameIcons.md`。

| 子集 | 上游 | 授权 | 许可文件 |
|---|---|---|---|
| Dream Strata Interface Icons | Phosphor Bold | MIT | `LICENSE-Phosphor-MIT.txt` |
| Dream Strata Material Icons | Material Design Icons 7.4.47 | Apache-2.0 | `LICENSE-MDI-Apache-2.0.txt`、`NOTICE-MDI.txt` |
| Dream Strata Dream Icons | Game-icons.net 20200315a | CC BY 3.0 | `LICENSE-GameIcons-CC-BY-3.0.txt`、`ATTRIBUTION-GameIcons.md` |

逐项来源、源 SHA256、作者页与拟议游戏码位见 `semantic-icons.json`；
说明汇总见 `SEMANTIC-ICON-LICENSES.md`。构建入口
`scripts/build_semantic_icon_fonts.py`；32 项储备只记录元数据，默认不打包。

## 项目改用 GPL 后的边界（2026-10-22）

项目代码改用 GPL-3.0-only，不改变以上字体、轮廓和图形的独立许可。
OFL 衍生字体继续 OFL-1.1；三个语义子集继续分别使用 MIT、Apache-2.0、CC-BY-3.0。
本项目原创图形研究稿已有的 `ICONS-LICENSE.txt` MIT 授权继续保留。

`DreamStrataUnified-Regular.ttf` 为物理合并字体，**2026-10-27 复核后已放行随包分发**：
合并来源是 OFL-1.1（正文底衬与图标轮廓）、MIT（Phosphor 派生）、Apache-2.0（MDI 派生）
与 CC-BY-3.0（Game-icons 派生）。四者均允许合并；上游许可文本与名称表均未声明
保留字体名，产物已整体改名为 Dream Strata 系列；产物 cmap 恰为“底衬 + 4 个子集”
的并集（33,826 码位，无额外来源）；逐源 SHA-256 与 `UPSTREAM-COPYRIGHTS.txt` 一致。
合并字体整体按 OFL-1.1 分发，嵌入的 MIT／Apache-2.0／CC-BY-3.0 轮廓保留各自许可，
四份许可全文、NOTICE-MDI 与逐项 Game-icons 署名随包分发。修改说明、证据与复核命令见
同目录 `UNIFIED-LICENSE-NOTICE.md`；完整项目许可范围见根目录 `LICENSING.md`。
# Interface Sans (2026-10-29)

DreamStrataInterfaceSans-Regular.ttf is derived from Noto Sans SC, Copyright
2014-2021 Adobe (http://www.adobe.com/), SIL Open Font License 1.1.
See InterfaceSans-OFL.txt for the upstream notice and full license.
Changes: upright weight 450, fixed 500/1000 terminal advances, shared baseline,
renamed family. Game icons and map glyphs retain the existing dedicated faces.
Source: https://github.com/google/fonts/tree/main/ofl/notosanssc
