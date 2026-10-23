# 梦层 / Oneirscript

*Rewrite the dream. Face what follows.*

**[简体中文](README_CN.md) · [English](README_EN.md)**

梦层是一款以潜意识为舞台的单人回合制 Roguelike。探索程序生成的梦境，组合装备语句，篡改描述现实的文字，并利用液体、气体和材料反应应对危机。

Oneirscript is a single-player, turn-based roguelike set in the subconscious. Explore generated dreamscapes, assemble equipment sentences, tamper with the words that describe reality, and turn environmental reactions into tactics.

## 阅读指南 / Guides

| 语言 / Language | 内容 / Contents |
|---|---|
| [简体中文 — README_CN.md](README_CN.md) | 游戏介绍、运行方式、操作与许可 |
| [English — README_EN.md](README_EN.md) | Overview, setup, controls, and licensing |

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

| 按键 / Key | 操作 / Action |
|---|---|
| WASD / 方向键 / Arrow keys | 移动 / Move |
| X | 观察 / Observe |
| Enter | 行动与确认 / Act and confirm |
| Tab | 行囊 / Inventory |
| N / B | 下潜／回溯 / Descend / Backtrack |
| Esc | 取消与暂停 / Cancel and pause |
| F10 | 保存并退出 / Save and quit |

完整操作以游戏内键位说明为准。See the in-game controls for the full key reference.

## 许可 / License

项目自有代码采用 [GPL-3.0-only](LICENSE)。字体、图标和音频保留各自的独立许可；详见 [许可边界](LICENSING.md)、[第三方声明](THIRD-PARTY-NOTICES.md)及 [音频署名](assets/CREDITS.md)。

Project-owned code is licensed under [GPL-3.0-only](LICENSE). Fonts, icons, and audio retain their separate licenses; see [licensing boundaries](LICENSING.md), [third-party notices](THIRD-PARTY-NOTICES.md), and [audio credits](assets/CREDITS.md).
