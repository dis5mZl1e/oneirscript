"""区域化界面主题：Header 底色/前景色、地图边框、**面板底色**随所在梦层区域变化。

三个区域各有一套主题（边框样式、边框色、顶栏底色/前景色、状态栏前景色、
**面板底色**），进入游戏或跨区换层时由 DreamApp 应用；主页不显示 Header，不应用主题。

🔴 2026-09-21 三改（玩家定稿）：
- **地图底色不再随区域上色，统一黑**（`MAP_BG`）。区域上色原本画在 `Screen` 上，
  实战问题有两个：①屏幕底色一变，玩家对「自己在地图哪一格」的距离感会跟着飘
  （移动时容易觉得错位）；②地形/墙体本身也吃到了底色的对比变化，反而更难辨认。
  所以地图回到「统一黑底 + 地形自己带显式底色」的老口径。
- **改由面板承担区域识别**（`RegionTheme.panel_bg`）：右侧状态面板 / 左侧浮层 /
  消息气泡三处底色跟着区域换，切换区域时一眼就能看出「换地方了」，而地图不动。
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..mapgen.layout import region_for_depth
from .realm_borders import REALM_BORDERS


@dataclass(frozen=True)
class RegionTheme:
    """一个区域的界面配色。border_style 是 Textual 边框线型名。"""

    border_style: str
    border_color: str
    header_bg: str
    header_fg: str
    status_fg: str
    # 面板底色（2026-09-21 三改）：画在右侧 `#side-pane` / 左侧浮层 `#map-overlay` /
    # 消息气泡 `#toast` 三处，**随区域换**——这是现在唯一的「区域识别色」。
    # 取值口径：亮度都压在 WCAG 相对亮度 0.021~0.026（与旧面板灰同级），
    # 只换色相（紫 / 青 / 洋红 / 烬红 / 中性），保证
    #   · 正文 #ffffff 对比度 13.8、键位提示 #9496b1 ≥ 4.8；
    #   · 与地图黑底 #101018 的对比度 ≥ 1.29（分得出「框里框外」）；
    #   · 任意两块面板一眼看得出不同（「区域识别」的全部意义）——判据分两种：
    #     两块都**有色**（HSV 饱和度 ≥ 0.20）→ 比色相角，要求 ≥ 20°；
    #     有一块是兜底**中性灰**（#292930，饱和度仅 0.15）→ 比饱和度，要求 ≥ 1.6 倍。
    # 🔴 兜底灰的「色相 240°」只是蓝通道多 7/255 的伪影，拿它跟 `梦的起始` 的
    # #2b2440 比色相会得出「只差 15°」的假结论——实际两者饱和度差 3 倍
    # （0.44 vs 0.15），肉眼分得很开。别用色相角去判一块灰。
    # ⚠️ 必须是**不透明**纯色：Textual 合成器会把 alpha 与下层预混，写 92% 之类
    # 反而会把地图的颜色透上来，既不是面板色、深浅还随地图内容变。
    panel_bg: str = "#292930"


REGION_THEMES: dict[str, RegionTheme] = {
    # 梦的起始（0 层）：黎明前的淡紫——圆角细线，柔和且无警示色。
    # 面板与其顶栏同色（#2b2440）：整块 UI 是一套淡紫，只有面板+顶栏两处着色，
    # 一个横条一个竖条，不会互相干扰。
    "梦的起始": RegionTheme(
        border_style="round",
        border_color="#8a7ac8",
        header_bg="#2b2440",
        header_fg="#e4ddff",
        status_fg="#d5ccff",
        panel_bg="#2b2440",
    ),
    # 浅层梦境（1 区）：安静柔和的蓝——圆角细线。
    # ⚠️ **开局就在这一层**（``GameState.new`` 的 depth=1），所以这块色是玩家
    # 看到的第一屏面板色，取值要一次到位。
    # 面板 = 偏青的蓝灰（#242e35）：与纯黑地图底对比 1.37（旧面板灰 #282e30 同档），
    # 「框里框外」分得很开。
    "浅层梦境": RegionTheme(
        border_style="round",
        border_color="#5a7ac8",
        header_bg="#232b4d",
        header_fg="#cfe0ff",
        status_fg="#b8ccff",
        panel_bg="#242e35",
    ),
    # 幻觉空间（2 区）：迷幻的紫红——双线。
    # 面板 = 洋红紫（#322337），色相 285°，与 1 区的 205° 差 80°——换区立刻看得出。
    "幻觉空间": RegionTheme(
        border_style="double",
        border_color="#b85ad2",
        header_bg="#341d4d",
        header_fg="#edd2ff",
        status_fg="#ddbcff",
        panel_bg="#322337",
    ),
    # 无意识领域（3 区）：深沉的烬红——粗线。
    # 面板 = 烬红（#352722），色相 16°，是五档里唯一的暖色，越深越「热」。
    "无意识领域": RegionTheme(
        border_style="heavy",
        border_color="#c8503a",
        header_bg="#38140f",
        header_fg="#ffcfb0",
        status_fg="#ffb894",
        panel_bg="#352722",
    ),
}

# 未知区域（异常深度）回落主题：与浅层一致但更中性。
# 深层边界（≥28 层）也走这里 —— 中性灰面板，不偏向任何一区。
DEFAULT_THEME = RegionTheme(
    border_style="round",
    border_color="#44445c",
    header_bg="#202028",
    # 兜底主题（未知区域 / 深层边界 ≥28）的文字色 = 亮白（与正文同口径）。
    header_fg="#ffffff",
    status_fg="#ffffff",
    panel_bg="#292930",
)

# 地图底色（2026-09-21 三改）：**全区域统一黑，不随区域变**。
# 它同时写两处，缺一不可（见 `app._apply_region_theme`）：
#   ① `Screen.background` —— 整块终端的最底层，铺满屏幕（含顶栏/底栏之间的缝隙）；
#   ② `#map-pane` 自己的 background —— 地图面板那一圈（边框 + padding）。
# ⚠️ 只写 ① 时，面板的边框/padding 圈靠「透明 → 透出 Screen 底色」得到颜色，
# 是**间接**的：面板自己没有底色，那一圈就不由面板负责重画（玩家实测：
# 地图边框那一圈留着旧底色）。面板自己有底色 = 换区时那一圈随面板一起重绘。
# 地形/液体/气体/光照/火焰全都自带显式底色（layered_background / 光照池 /
# jitter），会盖住它；只有「基帧没画任何显式底色」的格子（普通地板、未探索区、
# 面板缝隙）才透出这个色。因此它天然满足「不能影响上层颜色」这条硬约束。
MAP_BG = "#101018"

# 中性面板色：主页 / 暂停菜单等「不属于任何区域」的界面用，也是离开游戏时的复位值。
DEFAULT_PANEL_BG = "#292930"


# ── 梦中梦专属面板底色 ───────────────────────────────────────────────────
# 颜色沿用各自边框的色相方向并压暗，保证白色正文清晰，同时进入梦中梦时能
# 从面板本身辨认位面。主页和非梦中梦区域仍使用上方的既有主题色。
REALM_PANEL_BACKGROUNDS: dict[str, str] = {
    "door_corridor": "#382f1f",       # 黄铜门扉：暗青铜
    "toy_memories": "#382430",        # 彩色积木：暗莓红
    "ember_bridge": "#3b241e",         # 铜金裂纹：深烬红
    "ebbing_hall": "#1f333b",          # 青蓝潮纹：深潮青
    "millennium_garden": "#182a44",    # 像素霓虹：深蓝
    "library_palace": "#30243d",       # 金色书脊：墨紫
    "white_sanatorium": "#2d3739",     # 银白净环：冷调银灰
}

# realm 面板色变体缓存：key = f"{realm_id}:{基底 panel_bg}"。
# 🔴 必须缓存——frozen dataclass 的 replace() 每次都造**新对象**，而
# `app._apply_region_theme` 的「区域没变就跳过」缓存靠 `_applied_theme is theme`
# 对象同一性；不缓存 = 同一区域每帧拿到不同对象 = 每帧重写全部样式。
# key 用基底 panel_bg 而不是 depth：五档主梦主题的 panel_bg 互不相同，足以
# 区分基底，且跨同区各层（深度不同、主题同）命中同一缓存条目。
_REALM_PANEL_VARIANTS: dict[str, RegionTheme] = {}


def theme_for_realm(realm_id: str, depth: int) -> RegionTheme:
    """梦中梦取主题：非 realm 直接透传 theme_for_depth（同一对象，零开销）。

    已登记梦中梦使用专属边框与面板底色；顶栏和状态栏仍沿用主梦深度主题。
    """
    if not realm_id:
        return theme_for_depth(depth)
    base = theme_for_depth(depth)
    key = f"{realm_id}:{base.panel_bg}"
    variant = _REALM_PANEL_VARIANTS.get(key)
    if variant is None:
        panel_bg = REALM_PANEL_BACKGROUNDS.get(realm_id)
        variant = replace(base, panel_bg=panel_bg) if panel_bg else base
        border = REALM_BORDERS.get(realm_id)
        if border is not None:
            variant = replace(variant, border_style=border.line_style, border_color=border.color)
        _REALM_PANEL_VARIANTS[key] = variant
    return variant


def theme_for_depth(depth: int) -> RegionTheme:
    """按全局层数取区域主题。"""
    return REGION_THEMES.get(region_for_depth(depth), DEFAULT_THEME)
