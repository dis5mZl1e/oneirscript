# 统一字体（DreamStrataUnified-Regular.ttf）许可与来源通告

复核日期：2026-10-27。适用文件：`assets/fonts/DreamStrataUnified-Regular.ttf`
（15,365,688 B，SHA-256 `f80913884614b9403411cf81f20761d6c61b767e60edf874f85c8a9ee59df90d`，
构建脚本 `scripts/build_unified_game_font.py`，清单 `unified-font.json`）。

## 1. 结论

**该合并字体可以使用，并随桌面发行包分发。** 依据是下面 5 条可复核事实；措辞性质是
工程与许可条款层面的判断，不替代法务意见。

1. 组成部分的许可全部允许合并与再分发：OFL-1.1（正文底衬与地图/图标轮廓）、
   MIT（Phosphor 派生 Interface Icons）、Apache-2.0（Material Design Icons 派生）、
   CC-BY-3.0（Game-icons.net 派生）。四者均为宽松许可，无 copyleft 冲突。
2. **没有任何上游声明保留字体名（Reserved Font Name）**：`OFL.txt`、`NotoEmoji-OFL.txt`、
   `NotoColorEmoji-OFL.txt` 里的 `Reserved Font Name` 只出现在 OFL 第 3 节的通用定义句中，
   14 个上游字体文件的 name 表也没有该声明。合并产物因此不触发 OFL §3 的名称限制。
3. 产物已整体改名：族名/PostScript 名/typographic 名全部为 `Dream Strata Unified` /
   `DreamStrataUnified-Regular`，不含 Noto / Victor Mono / Phosphor / Material / Game-icons 等上游名。
4. 合并范围可逐码位核对：产物 cmap **33,826** 个码位 = 正文底衬 `DreamStrataSongReading-Regular`
   （33,209）∪ `DreamStrataIcons`（463）∪ `DreamStrataInterfaceIcons`（51）
   ∪ `DreamStrataMaterialIcons`（30）∪ `DreamStrataDreamIcons`（73），
   **并集外多余码位 0 个**，即没有第五个未声明的来源。
5. 逐源哈希一致：14 个构建输入文件的 SHA-256 与 `UPSTREAM-COPYRIGHTS.txt` 记录的期望值
   **逐项相同**（复核脚本见第 5 节），说明随包版权声明对应的确实是本次构建用的源文件。
   全部 10 个随包字体的 `OS/2.fsType = 0`（无嵌入限制）。

## 2. 许可集合与随包材料

| 组成部分 | 上游 | 许可 | 随包材料 |
|---|---|---|---|
| 正文底衬、拉丁、符号、冷门脚本 | Noto Serif SC / Noto Sans Symbols(2) / Math / Serif 系列、Victor Mono | OFL-1.1 | `OFL.txt`、`UPSTREAM-COPYRIGHTS.txt`、`LICENSES.md` |
| 地图与游戏图标轮廓 | Noto Emoji / Noto Sans Symbols(2) / Noto Sans Math / Noto Serif SC | OFL-1.1 | `NotoEmoji-OFL.txt`、`glyph-manifest.json` |
| Interface Icons 子集 | Phosphor Icons | MIT | `LICENSE-Phosphor-MIT.txt` |
| Material Icons 子集 | Material Design Icons 7.4.47（Pictogrammers） | Apache-2.0 | `LICENSE-MDI-Apache-2.0.txt`、`NOTICE-MDI.txt` |
| Dream Icons 子集 | Game-icons.net 20200315a | CC-BY-3.0 | `LICENSE-GameIcons-CC-BY-3.0.txt`、`ATTRIBUTION-GameIcons.md`（73 项逐条署名） |

## 3. 分发口径

- 合并字体**整体以 OFL-1.1 分发**（OFL §5 要求衍生字体不再另用其他许可）；
  其中嵌入的 MIT／Apache-2.0／CC-BY-3.0 轮廓**各自保留原许可**，不因物理合并被改写为 OFL，
  也不因此把游戏代码改为这些许可。
- OFL §1 的版权声明与许可全文、Apache-2.0 §4(a) 的许可全文与 NOTICE、
  MIT 的版权与许可、CC-BY-3.0 的许可与逐项署名，均随 `assets/fonts/` 与发行包根目录的
  `LICENSING.md`、`THIRD-PARTY-NOTICES.md` 一起分发。
- Apache-2.0 §4(b) 修改说明：上述图标轮廓经**子集化、等比缩放、重映射到私有区（PUA）
  槽位并与正文底衬物理合并**，未做非等比拉伸，也未新增语义；逐槽记录见
  `glyph-manifest.json`、`semantic-icons.json`。
- CC-BY-3.0 署名与来源页见 `ATTRIBUTION-GameIcons.md`；许可变更说明见本文件第 3 节。

## 4. 已知残留（不影响可发行性）

- 合并字体 name 表的 `nameID 0` 只写了底衬的版权行（`(c) 2017-2024 Adobe`），其余上游声明
  以 `UPSTREAM-COPYRIGHTS.txt` 随字体目录分发；若要让版权行也进入二进制，需重跑构建脚本。
- 合并字体 `nameID 7`（trademark）仍是旧的 `Dream Strata Serif Mono`（本项目自有名称，
  非上游名），属于从 `DreamStrataSongReading-Regular.ttf` 继承的文案残留。
- 该字体是构建候选（`unified-font.json` 中 `default: false`），当前默认字体仍是
  `DreamStrataSongReading-Regular.ttf`；两者的来源与许可是同一套。

## 5. 复核方法

```powershell
# 逐源哈希 / 名称表 / fsType
python build/_audit_release/upstream_verify.py
# 产物名称表、cmap 并集、OFL 保留字体名
python build/_audit_release/font_provenance.py
```

两份脚本的 JSON 产物：`build/_audit_release/upstream_verify.json`、
`build/_audit_release/font_provenance.json`。
