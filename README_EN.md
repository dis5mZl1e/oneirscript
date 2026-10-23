# Oneirscript / 梦层

[Home](README.md) · [简体中文](README_CN.md) · **English**

*Rewrite the dream. Face what follows.*

Oneirscript is a single-player, turn-based roguelike built with Python and Textual, set in the subconscious. Explore generated dreamscapes, assemble equipment sentences, tamper with the words that describe reality, and turn environmental reactions into tactics.

## Gameplay

- **Turn-based exploration:** observe your surroundings, choose a route, and weigh each action against its resource cost.
- **Equipment sentences:** combine conditions, targets, positions, and actions to shape your build.
- **Reality tampering:** change sentences describing objects and the environment while paying resource costs and accepting risks.
- **Environmental interactions:** use liquids, gases, fire, and conduction to deal with threats.
- **Dream descent:** explore the main dream and its branches, face deeper anomalies, and make your final choices.

## Run from source

Requires **Python 3.11 or later**. Download or clone the repository, then run these commands from its root directory:

```sh
python -m pip install -r requirements.txt
python run_demo.py
```

The recommended WezTerm terminal may need an internet connection on first launch. To use your current terminal instead:

```sh
python run_demo.py --compat-terminal
```

Chinese and English are available in the in-game settings. Startup options are in `game_config.ini`; saves are stored locally in `save/`.

## Basic controls

| Key | Action |
|---|---|
| WASD / Arrow keys | Move |
| X | Observe |
| Enter | Act and confirm |
| Tab | Inventory |
| N / B | Descend / Backtrack |
| Esc | Cancel and pause |
| F10 | Save and quit |

See the in-game controls for the full key reference.

## License

Project-owned code is licensed under [GPL-3.0-only](LICENSE). Fonts, icons, and audio retain their separate licenses.

- [Licensing boundaries](LICENSING.md)
- [Third-party notices](THIRD-PARTY-NOTICES.md)
- [Audio credits](assets/CREDITS.md)
