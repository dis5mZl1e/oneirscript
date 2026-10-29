"""地图声音标记（docs 261022 §16.4）。

普通听觉只给方向：未知声源只画角色附近的方向标，绝不把真实坐标当标记。
「听界」与「确认声源」才是显式授予的精确点；它们只标发声格与时刻，
不照亮周围地形、不返回隐藏实体、也不跟随声音搬家。
"""

from __future__ import annotations

from ..data.perception import CONFIRMED_SOURCE_RETENTION, LISTEN_REALM_TURNS

KNOWN_GLYPH = "·"
DIRECTION_GLYPH = "?"
CONFIRMED_GLYPH = "*"
LISTEN_GLYPH = "+"
SELECTED_GLYPH = "◆"
ASCII_SELECTED_GLYPH = "@"
# 方向标离角色两格，避免盖住玩家自己与贴身格。
DIRECTION_OFFSET = 2


def marker_glyph(glyph: str, *, ascii_mode: bool = False) -> str:
    """ASCII 档把声源点退回 .，选中标记退回 @。"""
    if ascii_mode and glyph == KNOWN_GLYPH:
        return '.'
    return ASCII_SELECTED_GLYPH if ascii_mode and glyph == SELECTED_GLYPH else glyph


def marker_legend(*, ascii_mode: bool = False) -> tuple[tuple[str, str], ...]:
    """观察层图例：字形与含义一一对应，不把普通方向标说成精确坐标。"""
    return (
        (KNOWN_GLYPH, "已辨向的近期声响"),
        (DIRECTION_GLYPH, "只知方向的声响"),
        (LISTEN_GLYPH, "听界发声点"),
        (CONFIRMED_GLYPH, "确认声源（保留 2 回合）"),
        (marker_glyph(SELECTED_GLYPH, ascii_mode=ascii_mode), "当前选中的线索"),
    )


def _fresh_clues(state) -> list[dict]:
    retention = state._clue_retention()
    return [clue for clue in state.heard_sound_clues
            if state.time - int(clue.get("time", 0)) < retention]


def _direction_point(state, sector: str) -> tuple[int, int] | None:
    dx = 1 if "东" in sector else -1 if "西" in sector else 0
    dy = 1 if "南" in sector else -1 if "北" in sector else 0
    if not (dx or dy):
        return None
    x = state.player.x + dx * DIRECTION_OFFSET
    y = state.player.y + dy * DIRECTION_OFFSET
    return (x, y) if state.inside_board(x, y) else (state.player.x, state.player.y)


def sound_markers(state, selected: int | None = None) -> dict[tuple[int, int], str]:
    """返回 ``{(x, y): 单字标记}``；``selected`` 是线索列表下标。"""
    markers: dict[tuple[int, int], str] = {}
    selected_pos = None
    for index, clue in enumerate(_fresh_clues(state)):
        if clue.get("known"):
            position = (int(clue.get("x", -1)), int(clue.get("y", -1)))
        elif clue.get("entry"):
            # 听诊器：已知到达侧的相邻墙面本身就是「从这里传来」的入口，
            # 但仍只放方向标，不把声源真实坐标当标记。
            entry = (int(clue["entry"][0]), int(clue["entry"][1]))
            position = entry if state.is_visible(*entry) else _direction_point(
                state, str(clue.get("sector", "")))
        else:
            position = _direction_point(state, str(clue.get("sector", "")))
        if position is None or not state.inside_board(*position):
            continue
        selected_here = index == selected
        if selected_here:
            selected_pos = position
            markers[position] = SELECTED_GLYPH
        elif position not in markers:
            markers[position] = KNOWN_GLYPH if clue.get("known") else DIRECTION_GLYPH

    # 精确点覆盖普通线索；被选中的线索仍优先显示高亮。
    if state.time < getattr(state, "listen_realm_until", 0):
        for entry in state.precise_sound_markers:
            if state.time - int(entry.get("time", 0)) >= LISTEN_REALM_TURNS:
                continue
            position = (int(entry.get("x", -1)), int(entry.get("y", -1)))
            if state.inside_board(*position) and position != selected_pos:
                markers[position] = LISTEN_GLYPH
    for entry in state.confirmed_sound_sources:
        if state.time - int(entry.get("time", 0)) >= CONFIRMED_SOURCE_RETENTION:
            continue
        position = (int(entry.get("x", -1)), int(entry.get("y", -1)))
        if state.inside_board(*position) and position != selected_pos:
            markers[position] = CONFIRMED_GLYPH
    return markers
