"""界面配色与节奏常量：地图/面板/征兆/观测各语义一色。"""

from __future__ import annotations


# 面板上「语义标记色」的统一替代（原先用命名色或压暗 hex，在最亮面板上只有 3.3~3.9）。
# 🔴 命名色会被 Textual 默认主题（Monokai 风）调色板解析成**偏暗**值，而且随主题变
# （实测：bright_red / bright_magenta → `#f4005f` 面板 3.30；bright_blue → `#9d65ff` 3.78；
# 反例：green / bright_green → `#98e024` 8.58、grey58 → `#949494` 4.56 是安全的）。
# 凡画在**面板**上的红 / 洋红 / 蓝一律改用下面这三个 hex；黑底页面（主页 / 图鉴 / 暂停）
# 用命名色无妨，那里对比度够。
# 第十九节 §10.1：面板字段的色值只有一个口径——`panel_fields.FIELD_COLORS` 注册表。
# 下面三个常量是它的别名，不再各留一份 hex；要改色只改注册表。
from .panel_fields import FIELD_COLORS as _F

PANEL_DANGER = _F['danger']    # 危险：失控意识 / 追踪 / 完整度告警 / 事件记录红点（面板 4.96）
PANEL_MAGENTA = _F['theme']    # 醒目：固定观察 / 特性 / 事件名 / 图鉴·地点图标（面板 6.51）
PANEL_BLUE = _F['category']    # 蓝色标识：液态记忆图标 / 观测·图鉴类别标签（面板 6.57）


AGGREGATE_STYLES = {"普通聚合物": "bright_green", "柔软聚合物": "green", "粗糙聚合物": "dark_green", "反光聚合物": "bright_white", "吸声聚合物": "grey70", "空白聚合物": "grey50", "木质聚合物": "#a8845c", "海绵聚合物": "#d8c890", "金属聚合物": "#9aa6b5", "灼热聚合物": "#e07038", "梦境绒毯": "#d8a8c8", "冰面": "#a8e0f0", "星图地": "#f0e8a8", "书页地": "#e8d8b0", "月壤": "#c8c4d4", "棋盘格地板": "#f0f0f0", "绝热层": "#b06828", "压电地板": "#68d8c8"}

# 聚合地面变体名的**面板专用**表：= 原表全量 + 面板安全覆盖（键与原表完全一致，不会漏项）。
# 同一个名字落在两个表面：① 地图上的地板字形（黑底 #101018）；② 右侧面板与格子详情里的
# 地板名（区域面板色，最亮 #242e35）。原表里几个刻意压暗的色在面板上「与背景太像」
# ——粗糙 dark_green 1.74 / 空白 grey50 3.50 / 木质 4.03 / 灼热 4.31 / 绝热层 3.20。
# 面板底色比地图亮 ⇒ 面板安全的色在地图上必然也安全，所以地图照用原表、面板走这张。
AGGREGATE_PANEL_STYLES = {
    **AGGREGATE_STYLES,
    "粗糙聚合物": "#39b54a",
    "空白聚合物": "#9e9e9e",
    "木质聚合物": "#c9a06a",
    "灼热聚合物": "#f08a52",
    "绝热层": "#cf8a3c",
}
# 物品分类配色（键 = ITEM_DEFINITIONS 的 category）。
# ⚠️ 「携带意象」= 所有能装入栏位的物品（原「装备」分类已于 2026-09-16 并入），
# 因此这里沿用原来的金色 —— 蓝色那条曾给旧的 9 件「携带意象」用，合并后即废弃。
CARRIED_IMAGE_STYLE = "#ffd166"
# 掉落物图标的字形在 symbols.SYMBOLS 里（带槽件按栏位 ✎/♖/⚜︎/⚒︎，无槽件 ◆），
# 显示时一律走 symbols.drop_glyph()——它会优先采用物品定义自带的 icon
# （书卷 📚 / 残页 📜），并把图标归一化为恰好两列。这里不再重复一份字面量
# （曾因不能 import symbols 而各留一份，现由 symbols 统一持有，避免两处慢慢走偏）。
CATEGORY_STYLES = {"携带意象": CARRIED_IMAGE_STYLE, "摄入物": "#b6e44c", "易逝物": "#ff8c42", "惯用物": "#d8d8d8", "记忆碎片": "#b18cff", "交互道具": "#46c6b0"}
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.text import Text  # 仅注解用

from ..rarity_colors import apply_rarity, item_variant_color



def _variant(item, color: str) -> str:
    """家族图标复用轮廓时，按（图标族, 底色）给同组物品分不同稳定配色。"""
    definition_id = getattr(item, "definition_id", "")
    return item_variant_color(definition_id, color) if definition_id else color


def item_display_color(item) -> str:
    """物品显示色：先按稀有度微调，再取家族图标的稳定变体色。"""
    color = getattr(item, "color", "") or "bright_white"
    rarity = getattr(item, "rarity", "")
    if rarity:
        color = apply_rarity(color, rarity)
    return _variant(item, color)


def item_name_color(item) -> str:
    """物品名显示色 = **物品自己的定义色**（2026-09-21 玩家要求：
    「不同物品不同颜色」——左侧面板/事件气泡/顶部播报里的物品名与地图
    掉落物图标同源同色，不再按分类染成六种固定色）。稀有度仍走四档微调。
    物品没有 color 字段时才回退分类色；共享家族图标的物品再做一次稳定分色。"""
    color = getattr(item, "color", None) or CATEGORY_STYLES.get(
        getattr(item, "category", ""), "bright_white"
    )
    rarity = getattr(item, "rarity", "")
    if rarity:
        color = apply_rarity(color, rarity)
    from .panel_fields import panel_color
    return panel_color(_variant(item, color))


def highlighted_message(message: str, base_style: str | None = None) -> "Text":
    """把一条消息翻成 Text，并给其中出现的**物品名**按各自的定义色高亮。

    事件气泡（FloatingToast）与标题栏播报（HeaderTicker）收到的都是纯
    字符串：旧写法整条白字，物品名与正文一个颜色。现在与事件记录
    （panels._message_text）同一口径——不同物品不同颜色。单个基样式可选。
    """
    from rich.text import Text

    text = Text(message, style=base_style or "")
    from ..core.content import ITEM_DEFINITIONS

    # ⚠️ ITEM_DEFINITIONS 的键是定义 id，「name」才是显示名——别拿名字当键查。
    matches = sorted(
        {d["name"]: d for d in ITEM_DEFINITIONS.values() if d.get("name") and d["name"] in message}.items(),
        key=lambda pair: len(pair[0]),
    )
    for name, definition in matches:
        color = definition.get("color") or CATEGORY_STYLES.get(definition.get("category"), "bright_white")
        text.highlight_words([name], style=color)
    return text


RELATION_STYLES = {"失控意识": '#ff6b60', "稳定意识": "#ffd60a", "受控意识": "#32d74b", "玩偶意识体": "#d9a0ff"}
# 第十九节 §5：面板关系词四色齐给，走同一张注册表；地图身份色 RELATION_STYLES 不动。
RELATION_PANEL_STYLES = {'失控意识': _F['danger'], '稳定意识': _F['mind'],
                         '受控意识': _F['imagination'], '玩偶意识体': _F['puppet']}


def realm_relation_style(realm_id: str, relation: str) -> str:
    """Return a relation color that stays legible on the current realm surface."""
    if relation == "稳定意识":
        if realm_id == "library_palace":
            return "#214f42"
        if realm_id == "white_sanatorium":
            return "#365d72"
    return RELATION_STYLES.get(relation, "white")


TRAUMA_STYLES = {"心智创伤": "#ff4fd8", "清醒创伤": "#36d6e7", "想象创伤": "#ffb000", "接触创伤": "#ff8095"}
INSIGHT_STYLE = _F["insight"]
# 征兆名统一使用与「◈ 征兆」导航按钮相同的紫色；效果说明一律灰色注释。
PORTENT_STYLE = _F["portent"]

# --------------------------------------------------------------------------- #
# 文字 / 背景对比度色阶（2026-09-21 定：面板底色改随区域换之后重新标定）
# --------------------------------------------------------------------------- #
# 面板底色在 5 档之间随区域换，**最亮的一档是「浅层梦境」`#242e35`
# （WCAG 相对亮度 0.0259）**。所以画在面板上的任何文字都必须对**最亮那档**也
# 达标——只照某一档调色，换到浅层就糊掉（玩家反馈「部分文字颜色与背景太像」
# 就是这么来的）。括号内 = 对最亮面板的对比度，全部 ≥4.5：
# 正文 = **亮白**（2026-09-21 玩家定稿：默认文字要一眼和面板底色分开）。
# 旧值 #a7a9c7 是偏冷的淡紫灰，在最亮面板上只有 6.03；纯白在最亮面板
# #242e35 上是 13.8，与各档面板色都拉得开。
PANEL_TEXT = _F["text"]      # 正文（13.8）
PANEL_MUTED = _F["muted"]    # 次要说明 / 注释 / 键位提示 / 占位（4.78）
# 状态栏第一行后半「层主题·层型」那一行。
# 🔴 原来写的是 `italic bright_magenta`——命名色会被 Textual 的主题调色板解析成
# **偏暗**的值（实测 bright_magenta → `#f4005f`，在最亮面板上只有 3.30），
# 而且解析结果随主题/终端变。改成 hex 后 6.51。
LAYER_LABEL_STYLE = "italic " + PANEL_MAGENTA
# 三条状态条的三档色（满 / 中 / 低）——同样**必须写 hex**：
# `bright_blue` 被解析成 `#9d65ff`（最亮面板 3.78），`blue` / `dark_blue` /
# `dark_goldenrod` 只会更暗。严重度改用**色相**表达（黄→橙→棕黄 / 蓝→深蓝 /
# 绿→深绿），三档都 ≥4.5（最低 4.56）。
BAR_MIND_STYLES = (_F["mind"], _F["mind_mid"], _F["mind_low"])
BAR_LUCIDITY_STYLES = (_F["lucidity"], _F["lucidity_mid"], _F["lucidity_low"])
BAR_IMAGINATION_STYLES = (_F["imagination"], _F["imagination_mid"], _F["imagination_low"])
# 进度条空槽：**故意**低对比（最亮面板 2.17），但要看得见「条有多长」——
# 旧的 `grey23` 只有 1.25，等于槽完全看不见，只能靠左对齐去猜。
BAR_TRACK = _F["track"]

# 征兆的性质/效果说明、各种面板小字（列表光标、滚动提示…）。
# 🔴 原值 `grey42` 在最亮面板上只有 2.64 —— 这些字其实等于看不见。
PORTENT_HINT_STYLE = PANEL_MUTED
# 观测面板：每个属性一个专属颜色，扫一眼就能把数值分门别类。
# （「攻击」在观测里曾写作攻击耗时——它其实是攻速；伤害另算，两者并列显示。）
OBSERVATION_ATTR_COLORS = {
    "耐久": _F["integrity"],
    "伤害": _F["damage"],
    "攻速": _F["time"],
    "移动": _F["time"],
    "视野": _F["range"],
    "创伤": _F["word"],
}
# 观测条目的「种类」标签（普通异象 / 强烈异象 / 核心执念）单独一色，
# 排在介绍之后。
OBSERVATION_KIND_COLOR = "#8ab4f8"
# 异象警戒状态：未察觉（沉静）→ 怀疑（起意）→ 警戒（锁定方向）→ 追踪（紧咬）。
# 观测详情里逐个体显示，用来解释「它为什么突然不追我了」（失去目标会降级）。
# 第十九节 §5：警戒四档显式 RGB（未察觉=亮灰、怀疑=程度金），命名色 grey58 退场。
ALERT_STYLES = {
    "未察觉": _F["muted"],
    "怀疑": _F["degree"],
    "警戒": _F["damage"],
    "追踪": _F["danger"],
}
GAME_FRAME_SECONDS = 1 / 30


def _beat_seconds(env_name: str, default_ms: int) -> float:
    """移动节拍的环境变量入口（A/B 实机对比用，默认值保持不变）。

    DREAM_MOVE_REPEAT_MS=90/110/130 与 DREAM_HOLD_RELEASE_MS=200/250/300
    可分别对比「首步后节奏」与「松键判定」；钳在 50–600ms，避免误配把
    走路变成瞬移或停不下来。
    """
    import os
    try:
        ms = float(os.environ.get(env_name, default_ms))
    except (TypeError, ValueError):
        ms = float(default_ms)
    return max(0.05, min(0.60, ms / 1000.0))


# 长按方向键的移动节拍：终端重复发送的按键事件只作为“仍按住”的证据，
# 移动统一由 30fps 帧定时器按此节拍执行，保证移动判定与渲染同步、逐格呈现。
MOVE_REPEAT_MIN_SECONDS = _beat_seconds("DREAM_MOVE_REPEAT_MS", 110)
# 终端不发送按键释放事件：超过该时长没有收到重复按键即视为已松开。
HOLD_RELEASE_TIMEOUT = _beat_seconds("DREAM_HOLD_RELEASE_MS", 250)
# 右侧五个面板模式：方向键走这里，Esc 关闭这里，其它游戏按键绕过这里。
RIGHT_PANEL_MODES = ("inventory", "equipment", "portents", "insights", "catalog", "tasks", "actions", "build_overview", "self_overview", "journal_log", "nearby", "self_stats", "sidebar_detail")
# 右侧面板**同一按钮界面内部**的分层（2026-10-23 用户定稿）：面板顶部的
# 小页签，点击或 ←→ 切换；到头停留，Alt+←→ 单独切换六个工作区。
# inventory 的分层直接复用既有物品分类筛选值（默认「全部」）。
PANEL_SUBPAGES = {
    "inventory": ("全部", "携带意象", "摄入物", "易逝物", "交互道具", "惯用物"),
    "equipment": ("board", "memory"),
    "actions": ("constructs", "fire", "tamper"),
}
PANEL_SUBPAGE_LABELS = {
    "board": "装备盘",
    "memory": "记忆碎片",
    "constructs": "构想",
    "fire": "发射",
    "tamper": "篡改",
}
PANEL_SUBPAGE_DEFAULTS = {
    "inventory": "全部",
    "equipment": "board",
    "actions": "constructs",
}
# 主页专属的面板模式：只在 home_mode 下合法，绝不能带进游戏（否则右侧会残留
# 「存档槽/开始新游戏」文案，且 panel_mode != "world" 会把按键路由卡在面板分支，
# 表现为小键盘去动面板光标而不是移动玩家）。见 DreamApp._sync_home_cursor。
HOME_PANEL_MODES = ("home", "home_saves", "home_catalog", "home_settings", "home_newgame")

# 地图缩放档位（Ctrl+↑/↓ 或 Ctrl+滚轮）：
# zoom 是视野比例——每格恒定渲染一个符号（2×1 终端列），
# zoom>1 放大（可见格数变少、格与符号同步“变大”），zoom<1 缩小
# （可见格数变多；最小 0.5 为紧凑概览档，
#  每格一列但仍使用主题 Unicode 字形；受地图实际尺寸钳制）。
MAP_ZOOM_LEVELS = (0.5, 1.0, 2.0, 3.0, 4.0)
MAP_DEFAULT_ZOOM = 1.0
