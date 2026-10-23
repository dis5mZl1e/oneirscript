"""字形与几何工具：Unicode 探测、两列宽归一化、视口原点、分层背景色。"""

from __future__ import annotations

import sys

from rich.cells import cell_len, set_cell_size
from rich.text import Text

from ..core import GameState
from ..materials import CONTAINER_KINDS, gas_def, liquid_def
from .styles import GAME_FRAME_SECONDS  # noqa: F401  （保持旧模块属性可见）

_UNICODE_CACHE: dict[str, bool] = {}


def _unicode_mode(unicode_mode: bool | None) -> bool:
    if unicode_mode is not None:
        return unicode_mode
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    cached = _UNICODE_CACHE.get(encoding)
    if cached is None:
        try:
            "❤@𓃡𓀠𓀃♙♟☻⋂✍⚚██░░∿≈≋· ·┃╬⧉𓆟✂☂⌂❖♬⌗☼▤◍◈▢≡▚⌁◌⚱🛢▲◎⧗▨△❀♣ψ❁ϟ✾∮⁂◈♪◕⇧𓆗☃❥࿐□↯ω".encode(encoding)
            cached = True
        except UnicodeEncodeError:
            cached = False
        _UNICODE_CACHE[encoding] = cached
    return cached


def gas_depth_key(gas: int) -> str:
    """气体浓度 → 图标键：1–5 ○（稀）、6–15 ◘（中）、16+ ●（浓）。
    三档使用明显不同的圆形/点纹/实心图标；颜色仍按气体种类区分、同种气体三档同色。"""
    if gas >= 16:
        return "gas.high"
    if gas >= 6:
        return "gas.mid"
    return "gas.faint"


def gas_glyph(amount: int, mode: str = "themed") -> str:
    """所有气体展示共用浓度纹理；气体种类仍由名称和颜色表达。"""
    from ..symbols import symbol
    return symbol(gas_depth_key(amount), mode)


def normalize_tile_glyph(glyph: str, mode: str = "themed", *, continuous: bool = False) -> str:
    """将地图符号归一化为恰好两列，避免窄字符贴边或宽字符溢出。"""
    glyph = glyph.strip()
    if mode == "themed" and not continuous and len(glyph) == 2 and glyph[0] == glyph[1]:
        glyph = glyph[0]  # 大型回退字形禁止双写，剩余列留作字形间距。
    width = cell_len(glyph)
    if width == 1:
        # 窄字符占一个终端列时，把空余列放在右侧，避免地格点号贴到格子末端。
        glyph = glyph + " "
    return set_cell_size(glyph, 2)


def compact_tile_glyph(glyph: str, mode: str = "themed") -> str:
    """把主题图标压到一个终端列，保留 Unicode 而不是退化成 ASCII。

    紧凑地图档位仍需要每个地图格恰好占一列，否则相邻格会发生错位。
    大多数主题图标本来就是“字形 + 空格”或重复双字形，取首个可见
    字形即可；对终端报告为双宽的字符，set_cell_size 会安全裁剪到一列。
    """
    del mode
    raw = glyph.strip()
    if not raw:
        return " "
    # 去掉尾部空格；保留变体选择符（如 ✂︎）以维持文本图标外观。
    first = raw[0]
    if len(raw) > 1 and raw[1] in ("\ufe0e", "\ufe0f"):
        first += raw[1]
    compact = set_cell_size(first, 1)
    # Rich 对部分双宽字符裁剪后会返回空白；仍保留原始 Unicode 字符，
    # 宁可让该单格按终端实际宽度显示，也绝不替换成 ASCII 问号。
    if not compact.strip() or ord(first[0]) > 0xffff:
        from ..symbols import NARROW_BY_GLYPH
        return NARROW_BY_GLYPH.get(glyph, "?")[:1]
    return compact


def viewport_origin(
    state: GameState,
    viewport_width: int,
    viewport_height: int,
    current: tuple[int, int] | None = None,
) -> tuple[int, int]:
    max_left = max(0, state.width - viewport_width)
    max_top = max(0, state.height - viewport_height)
    if current is not None:
        left, top = current
        left = max(0, min(left, max_left))
        top = max(0, min(top, max_top))
        # 相机死区：玩家在视口中部移动时保持视口不动；
        # 越出死区后每次只平移“溢出的格数”（连续移动时即为 1 格），
        # 让视口逐格跟随玩家，而不是一次性重新居中造成突兀跳动。
        # 小视口不能强制保留 1 格边距；1×1 时边距必须为 0，
        # 否则右/下边界公式会把相机原点推到玩家后一格。
        margin_x = min(max(1, viewport_width // 3), (viewport_width - 1) // 2)
        margin_y = min(max(1, viewport_height // 3), (viewport_height - 1) // 2)
        local_x = state.player.x - left
        local_y = state.player.y - top
        if local_x < margin_x:
            desired_left = left - (margin_x - local_x)
        elif local_x >= viewport_width - margin_x:
            desired_left = left + (local_x - (viewport_width - margin_x - 1))
        else:
            desired_left = left
        if local_y < margin_y:
            desired_top = top - (margin_y - local_y)
        elif local_y >= viewport_height - margin_y:
            desired_top = top + (local_y - (viewport_height - margin_y - 1))
        else:
            desired_top = top
        return max(0, min(desired_left, max_left)), max(0, min(desired_top, max_top))
    left = state.player.x - viewport_width // 2
    top = state.player.y - viewport_height // 2
    return max(0, min(left, max_left)), max(0, min(top, max_top))


def liquid_depth_key(amount: int) -> str:
    """液体符号按深度分档：越深波线越多；种类由颜色区分。"""
    if amount >= 67:
        return "liquid.deep"
    if amount >= 34:
        return "liquid.medium"
    return "liquid.shallow"


def darken(color: str, factor: float = 0.4) -> str:
    """把 #rrggbb 颜色按系数变暗，用作背景色避免喧宾夺主。

    解析失败时原样返回（rich 样式名如 bright_red 不在此处理，
    调用方应只传十六进制色）。
    """
    if not color.startswith("#") or len(color) != 7:
        return color
    try:
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
    except ValueError:
        return color
    return "#{:02x}{:02x}{:02x}".format(
        round(red * factor), round(green * factor), round(blue * factor)
    )


def layered_background(cell, foreground: str = "auto") -> str | None:
    """计算格子的背景色：被前景符号压住的最高下层颜色。

    分层（前景优先级：生物 = 墙体 > 气体 > 液体 = 地面非墙固体 > 地面）：
    前景为实体/物品/火焰/墙体时，背景取其下最高层——气体色（按遮挡度降亮度）
    或液体色（按液量降亮度）；前景为气体时背景取液体色（气在液上，液色透出）。
    foreground="auto" 时按格内最高内容物判定（供悬停等无前景上下文调用）。
    无下层内容时返回 None（使用默认背景）。

    地面容器（记忆容器/思绪容器）是低矮的封存固体：数据上占实心格、阻挡液体
    流动，但内容物就在格内供玩家观察（2026-10-22 用户反馈修复）。因此只对
    CONTAINER_KINDS 放开 not cell.solid 限制——容器图标作为前景时仍能透出
    气体（优先）或液体的暗底色；高墙/台子等其它 solid 的行为完全不变，不会
    因为这条改动开始透出液气颜色。
    """
    container = str(getattr(cell, "wall_kind", "") or "") in CONTAINER_KINDS
    permeable = (not cell.solid) or container
    # 液体背景：液量越多背景越明显；非容器墙体格不透液体（高墙阻挡）
    if cell.liquid > 0 and permeable:
        liquid_definition = liquid_def(cell.liquid_kind)
        liquid_factor = 0.35  # Stable material identity; quantity is conveyed by the glyph.
        liquid_bg = darken(liquid_definition.color, liquid_factor)
    else:
        liquid_bg = None
    # 液体在气体之上（图层已交换）：前景为液体时透气体色。
    if foreground == "liquid":
        if cell.gas > 0 and permeable:
            gas_definition = gas_def(cell.gas_kind)
            return darken(gas_definition.color, 0.32)
        return None
    # 前景为气体时只透液体，前景更高（或 auto）时透气体
    if foreground == "gas":
        return liquid_bg
    if cell.gas > 0 and permeable:
        gas_definition = gas_def(cell.gas_kind)
        gas_factor = 0.32  # 0.25~0.6
        return darken(gas_definition.color, gas_factor)
    return liquid_bg


def with_background(style: str, background: str | None) -> str:
    """把背景色拼进 rich 样式串。"""
    return f"{style} on {background}" if background else style
