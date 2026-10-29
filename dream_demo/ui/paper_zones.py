"""右栏「纸感分区」色板（2026-10-24 批次）。

设计（玩家定稿的方向）：右栏是一张摊在桌上的纸，内部按功能分成几块
纸区，而不是一整块同色面板——

- **固定纸色系**：六档分区色**不随区域主题换**。区域识别仍由既有三件套
  承担（边框 / 顶栏 / 缝隙，见 `region_themes`），纸色只表达「这是纸上
  哪一块」，换区时纸不动。
- **desk 露缝**：`#side-pane` 本体仍是区域 `panel_bg`（「桌面」）；分区
  之间未上色的行（#sidebar-tools、#signal-status 等）与缝隙透出桌面，
  分区色只铺在分区本体上。
- **底色一律不透明纯色**：hex 直写、不带 alpha——Textual 合成器会把
  alpha 与下层预混（tests/test_panel_backgrounds.py 的既有结论）。

口径：
- **亮度**：全部分区底色 WCAG 相对亮度 ≤0.05（`panel_fields.luminance`）。
- **对比**：写在某分区上的文字色对该分区底 ≥4.5；各分区的文字集合见
  `ZONE_TEXT_COLORS`（tests/test_paper_zones.py 逐档验收）。三资源条的
  *_mid/*_low 档只画在封面区（#status），因此只需对 ZONE_COVER 达标。
- **两两可分**：任两个分区色必须满足「色相差 ≥20° 或 亮度比 ≥1.25 或
  饱和度比 ≥1.6」（HSV 饱和度，与 tests/test_panel_backgrounds 的
  _chroma 同口径）。

与批次给定值的偏差（两处，均为满足两两可分判据的最小调整）：
- ZONE_NOTE #38351c → #32371a：给定值与封面只差 14.3° 色相、1.08 倍
  亮度、1.12 倍饱和度，三条判据全不达标；把便签推向黄橄榄（hue ≈70°）
  后与封面差 31°、与牛皮条差 38°。亮度 0.0349 仍低于 panel_color 的
  兜底底色 #2d3739（0.0359），悬停文本里经 panel_color 提亮的素材色
  对便签底的保证（≥4.5）原样成立。
- ZONE_STRIP #443722 → #443a2e：给定值与激活标签亮度只差 1.15 倍、
  饱和度只差 1.14 倍，分不出来；把牛皮条去饱和（0.50 → 0.32）后与
  激活标签饱和度比 1.75、与封面亮度比 1.39；在正文底（ZONE_BODY）上
  亮度 1.78 倍，通栏条读起来是「浮在纸上的一条」。
"""
from __future__ import annotations

from .panel_fields import FIELD_COLORS
from .region_themes import DEFAULT_THEME, REGION_THEMES
from .styles import (
    BAR_IMAGINATION_STYLES,
    BAR_LUCIDITY_STYLES,
    BAR_MIND_STYLES,
    PANEL_MAGENTA,
    PANEL_TEXT,
    PORTENT_HINT_STYLE,
)

# ---- 分区底色（不透明纯色；设计口径见文件头） ----
ZONE_COVER = '#3a3120'      # 牛皮纸封面 · 状态区（#status）
ZONE_NOTE = '#32371a'       # 淡黄便签 · 地形叙述（#hover-info）
ZONE_TABS = '#332b1b'       # 标签行（#panel-tabs / #panel-sections）
ZONE_TAB_ACTIVE = '#4a3b20' # 激活标签（.sidebar-active 的小色块）
ZONE_BODY = '#2e2c22'       # 米白正文（#panel）
ZONE_STRIP = '#443a2e'      # 通栏牛皮条（分组标题条 / 滚动提示）

ZONES = {
    'ZONE_COVER': ZONE_COVER,
    'ZONE_NOTE': ZONE_NOTE,
    'ZONE_TABS': ZONE_TABS,
    'ZONE_TAB_ACTIVE': ZONE_TAB_ACTIVE,
    'ZONE_BODY': ZONE_BODY,
    'ZONE_STRIP': ZONE_STRIP,
}

# ---- 同族纸分区（2026-10-24 深化批次：块内分块）----
# 环境页与构想页把正文区再切成左右/上下两块。口径与主分区**不同**：成对出现、
# 刻意「同族近似」——同是暗纸、亮度差 <1.25，只靠色相区分；因此**不进** ZONES
# 的两两可分表（进了会被主判据否决），约束单独立（tests/test_paper_zones.py）：
# 不透明、亮度 ≤0.05、不亮于 ZONE_BODY（正文区文字对比口径随 BODY 成立）、
# 环境对内色相差收在 30°~60°（「略微不同」），构想对更醒目（60°~130°）。
ZONE_ENV_ENTITIES = '#292b23'   # 环境页·左（异象清单）：橄榄纸（hue≈75°）
ZONE_ENV_SURVEY = '#2b261f'     # 环境页·右（环境概述）：暖褐纸（hue≈35°）
ZONE_CAST_LIST = '#252c2b'      # 构想页·构想列表块：灰青纸（hue≈171°）
ZONE_CAST_PREVIEW = '#2b2630'   # 构想页·使用预览块：灰紫纸（hue≈270°）

SIBLING_ZONES = {
    'ZONE_ENV_ENTITIES': ZONE_ENV_ENTITIES,
    'ZONE_ENV_SURVEY': ZONE_ENV_SURVEY,
    'ZONE_CAST_LIST': ZONE_CAST_LIST,
    'ZONE_CAST_PREVIEW': ZONE_CAST_PREVIEW,
}

# 分栏细竖线：缝不是字——track 灰按第十九节 §10.4 的空轨豁免，不进对比集合。
SPLIT_DIVIDER_STYLE = FIELD_COLORS['track']

# 工作区页签文字（#nav-* 按钮，画在标签行与激活标签两块底上）。
# inventory 原为 #44aaff：对激活标签底只有 4.36，按批次口径提亮一档
# （4.63），其余五区沿用既有类别色。
TAB_INK_INVENTORY = '#44b1ff'
TAB_INKS = (
    TAB_INK_INVENTORY,
    FIELD_COLORS['label'],
    '#ffd166',
    '#c9a0ff',
    '#ff8c42',
    '#73dfb1',
)

# 滚动提示改「细牛皮条」：muted 字 + 通栏 ZONE_STRIP 底（_panel_scroll_hint）。
SCROLL_HINT_STYLE = PORTENT_HINT_STYLE + f' on {ZONE_STRIP}'

# 各区域主题的状态栏前景色（_apply_region_theme 会把它写到 #status 上），
# 去重后进封面区的文字集合——status_fg 是为 panel_bg 调的，换封面底后必须仍可读。
STATUS_FGS = tuple(dict.fromkeys(
    theme.status_fg for theme in (*REGION_THEMES.values(), DEFAULT_THEME)
))

# ---- 各分区的文字色集合（验收口径，tests/test_paper_zones.py 消费） ----
# 只列「真的画在这块底上」的颜色；背景元素（进度条空轨 track）按第十九节
# §10.4 的既有豁免不进集合。
ZONE_TEXT_COLORS = {
    # 封面区：地区行/崩解行正文白（Rich 与 Textual 两种 white 解析都收）、
    # 层标签洋红、三资源条全档（含中低档）、合并行噪音/混乱、深层边界/
    # 可下潜两支、区域主题 status_fg。
    'ZONE_COVER': (
        PANEL_TEXT, '#c4c5b5', PANEL_MAGENTA,
        *BAR_MIND_STYLES, *BAR_LUCIDITY_STYLES, *BAR_IMAGINATION_STYLES,
        FIELD_COLORS['noise'], FIELD_COLORS['chaos'],
        '#3ddad0', '#98e024', '#00ff00',
        *STATUS_FGS,
    ),
    # 便签区：地形叙述正文白 + 次要灰；素材名走 panel_color 兜底底色
    # #2d3739 提亮，本区亮度更低所以保证原样传递（测试另有断言钉住）。
    'ZONE_NOTE': (PANEL_TEXT, FIELD_COLORS['muted']),
    # 标签行 / 激活标签：六区页签文字 + 分类按钮标签。
    'ZONE_TABS': (*TAB_INKS,),
    'ZONE_TAB_ACTIVE': (*TAB_INKS,),
    # 正文区：面板注册表全量语义色（track 空轨豁免）+ 正文白。
    'ZONE_BODY': (PANEL_TEXT, *(c for k, c in FIELD_COLORS.items() if k != 'track')),
    # 牛皮条：分组标题沿用各组的语义色，另含滚动提示 muted 与正文白。
    'ZONE_STRIP': (
        FIELD_COLORS['word'], FIELD_COLORS['identity'], FIELD_COLORS['condition'],
        FIELD_COLORS['heading'], PANEL_TEXT, FIELD_COLORS['muted'],
    ),
    # 同族纸分区：画在上面的字与正文区同一套（列表/统计/预览全用注册表色）。
    'ZONE_ENV_ENTITIES': (PANEL_TEXT, *(c for k, c in FIELD_COLORS.items() if k != 'track')),
    'ZONE_ENV_SURVEY': (PANEL_TEXT, *(c for k, c in FIELD_COLORS.items() if k != 'track')),
    'ZONE_CAST_LIST': (PANEL_TEXT, *(c for k, c in FIELD_COLORS.items() if k != 'track')),
    'ZONE_CAST_PREVIEW': (PANEL_TEXT, *(c for k, c in FIELD_COLORS.items() if k != 'track')),
}
