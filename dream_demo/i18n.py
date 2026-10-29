"""多语言支持：语言包机制与切换。

设计：
- 所有代码继续以中文原文作为**键**（与现有数据定义一致，零迁移成本）；
  ``tr(原文)`` 在渲染/显示点把原文替换为当前语言包里登记的译文，
  未登记的键原样返回——因此默认中文显示与行为完全不变。
- ``LANGUAGE_PACKS`` 内置 ``zh``（空表 = 原文）与 ``en``；键为语言名，
  与设置项 ``language`` 的取值一致。外部语言包只需提供同构的字典。
- 图标、emoji、地图符号是跨语言固定的，**不参与翻译**。
- 切换语言（设置页调整 ``language``）调用 :func:`set_language`，
  因为所有显示点在每次刷新时经 ``tr`` 取词，切换即时生效。

覆盖范围：界面文案 + 全部内容名称（异象/物品/墙/液/气/征兆/事件/洞察）。
描述长文与运行中生成的消息保留原文（缺键回退原文），后续语言包可逐步补齐。
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "zh"

# 当前激活语言；仅通过 set_language 修改。
_active_language: str = DEFAULT_LANGUAGE


def set_language(language: str) -> None:
    """切换当前语言；未知语言回退默认（中文原文）。"""
    global _active_language
    _active_language = language if language in LANGUAGE_PACKS else DEFAULT_LANGUAGE


def get_language() -> str:
    return _active_language


def tr(text: str, /, **fields: object) -> str:
    """把原文（中文键）翻译为当前语言；未登记的键原样返回。

    可选的 ``fields`` 用于**模板插值**：译文（或中文原文）里的 ``{名字}``
    会按关键字替换。运行中生成的事件记录因此既能保留一条可读的中文原文，
    又能在英文下按 ``tr(template, item=..., count=...)`` 一次性落地。
    不给 ``fields`` 时行为与纯查表完全一致（不触发 ``str.format``）。
    """
    if _active_language == DEFAULT_LANGUAGE:
        rendered = text
    else:
        rendered = LANGUAGE_PACKS.get(_active_language, {}).get(text)
        if rendered is None and _active_language == 'en':
            from .i18n_realms import translate_composed
            rendered = translate_composed(text)
        if rendered is None:
            rendered = text
    if fields:
        try:
            return rendered.format(**fields)
        except (KeyError, IndexError, ValueError):
            # 占位符不匹配（译文写错、或原文里本就有花括号）时退回未插值文本，
            # 绝不因为一条文案把整局游戏打断。
            return rendered
    return rendered


EN: dict[str, str] = {
    # ---- 界面 ----
    "梦 层": "ONEIRSCRIPT",
    "入梦之前，先选好一段位置。": "Pick a resting place before you descend.",
    "入梦": "Enter Dream",
    "Enter 进入 · ←→ 选槽/删除 · 数字 1/2/3 直选 · Esc/Q 返回":
        "Enter to load · ←→ slot/delete · 1/2/3 quick-pick · Esc/Q back",
    "选择一个存档槽入梦": "Choose a save slot to descend",
    "存档槽": "Slot",
    "继续": "Continue",
    "新游戏": "New Game",
    "删除": "Delete",
    "图鉴": "Codex",
    "设置": "Settings",
    "退出": "Quit",
    # 全屏暂停菜单（Esc：返回/菜单双语义）。
    "返回主页": "Back to Home",
    "返回/菜单": "Back/Menu",
    "暂 停": "P A U S E D",
    "↑↓/W S/滚轮 选择 · Enter/左键 确认 · Esc 继续": "↑↓/W S/Wheel select · Enter/Click confirm · Esc resume",
    "行囊": "Bag",
    "征兆": "Omens",
    "洞察": "Insights",
    "观测": "Observe",
    "操作": "Act",
    "Tab 行囊  t 携带意象  v 征兆  i 洞察  k 观测  ? 操作  \\ 注释  g 捡起  Ctrl+↑↓ 缩放": "Tab Bag  t Carried  v Omens  i Insights  k Observe  ? Act  \\ Notes  g Pick up  Ctrl+↑↓ Zoom",
    "Tab 行囊  t 携带意象  v 征兆  i 洞察  k 观测  ? 操作  \\ 注释  ]+左键 展开  右键/ ' 键详细信息  WASD 面板 · ←↑↓→/小键盘 移动": "Tab Bag  t Carried  v Omens  i Insights  k Observe  ? Act  \\ Notes  ]+Click Expand  Right-click / ' = details  WASD Panel · ←↑↓→/Numpad Move",
    # 底栏可点击键位与物品菜单的键名（"保存并退出" / "返回/投掷" 已在下文登记，勿重复）。
    "行动": "Do",
    "观察": "Look",
    "下潜": "Descend",
    "上浮": "Backtrack",
    "捡起": "Pick up",
    "等待": "Wait",
    "使用": "Use",
    "卸下": "Unequip",
    "放下": "Drop",
    "投掷": "Throw",
    "原地点燃": "Ignite Here",
    # §11 H1 听觉线索：八方位、距离档与声音大类。
    "北": "North", "南": "South", "东": "East", "西": "West",
    "东北": "Northeast", "东南": "Southeast", "西北": "Northwest", "西南": "Southwest",
    "近距": "Near", "中距": "Mid", "远距": "Far", "极远": "Very Far",
    "脚步": "Footsteps", "主动诱引": "Active lure", "道具": "Item",
    "投射物": "Projectile", "爆炸": "Explosion", "墙体破坏": "Wall break",
    "瓷墙碎裂": "Porcelain shatter", "环境": "Environment", "呼喊": "Shout",
    "构想": "Construct", "响动": "Noise", "听觉线索": "Hearing clues",
    "方向与距离可知，位置未知": "direction and distance known, position unknown",
    "{sector} · {band} · {category} · {where}": "{sector} · {band} · {category} · {where}",
    "{sector} · {band} · {category} · {where} · 第 {turn} 回合": "{sector} · {band} · {category} · {where} · turn {turn}",
    "{sector} · {category} · {where} · 第 {turn} 回合": "{sector} · {category} · {where} · turn {turn}",
    "远近档需要「听声辨向」：等待一次后四个回合内显示。": "Range bands need “Sound Bearing”: shown for four turns after waiting once.",
    "线索保留 {n} 个真实回合；未知声源不给敌名与精确坐标。": "Clues last {n} real turns; unknown sources reveal no names or exact coordinates.",
    "雨声的遮蔽 −{n}": "Rain sound cover −{n}",
    "忙音的间距 +{n}": "Dial-tone spacing +{n}",
    "尖啸瓷墙碎裂": "Screaming porcelain shatter",
    "借声藏步 ×0.5": "Borrowed Footfalls ×0.5",
    "噪声耐受：本次不放大": "Noise Tolerance: no amplification this time",
    "你贴着沉思铁幕等待，借振动记下 {walls} 个墙格的 {entries} 处开放入口。": "You wait against the Thought-Iron Curtain and map {entries} open entries across {walls} wall cells by vibration.",
    "你借着身旁的光，记下 {n} 格地形。": "You use the nearby light to record {n} tiles of terrain.",
    "碎裂的地形深深刻进灰烬记忆。": "The shattered terrain is etched into Ash Memory.",
    "蜂鸣回响：广播加成已开启。": "Buzzing Echo: broadcast bonus enabled.",
    "蜂鸣回响：广播加成已关闭。": "Buzzing Echo: broadcast bonus disabled.",
    "广播加成：开启（Enter 关闭）": "Broadcast bonus: on (Enter to disable)",
    "广播加成：关闭（Enter 开启）": "Broadcast bonus: off (Enter to enable)",
    "液体 {kind} {n}": "Liquid {kind} {n}",
    "气体 {kind} {n}": "Gas {kind} {n}",
    "火焰 {n}": "Flame {n}",
    "通行代价 {n}": "Traversal cost {n}",
    "上次观察（第 {turn} 回合）：{parts}": "Last observed (turn {turn}): {parts}",
    "地上:": "Ground: ",
    "意识行囊": "Mind Inventory",
    "事件记录": "Event Log",
    "记忆槽：": "Memory Slots: ",
    "空": "empty",
    "尚未形成洞察": "No insights formed yet",
    "此刻没有萦绕在你身上的征兆": "No omens cling to you right now",
    "视野中没有失控意识": "No stray consciousness in sight",
    "选择存档槽": "Choose save slot",
    "已选择存档槽": "Selected slot",
    "按 Enter 进入，按 D 删除。": "Press Enter to enter, D to delete.",
    "按 Enter 开始新游戏。": "Press Enter to start a new game.",
    "左键点击进入，按 D 删除。": "Left-click to enter, D to delete.",
    "左键点击开始新游戏（Enter 不再开新游戏）。": "Left-click to start a new game (Enter no longer starts one).",
    "终端输入和颜色沿用当前配置。": "Terminal input and colors follow the current settings.",
    "悬停观察 无": "Hover inspect: none",
    "位置:": "Pos:",
    "悬停:": "Hover:",
    "观察:": "Look:",
    "地板:": "Floor:",
    "表面:": "Surface:",
    "高处:": "High:",
    "空中:": "Air:",
    "贴近：": "Nearby: ",
    "梦层": "Layer",
    "心智": "Mind",
    "清醒度": "Lucidity",
    "想象力": "Imagination",
    "档": "Tier",
    "崩解度": "Dissolution",
    "回合数": "Rounds",
    "发射": "Fire: ",
    "已解锁": "unlocked",
    "聚合弹": "charges",
    "近处观察：": "Nearby: ",
    "无": "none",
    "未定形轮廓": "An unformed outline",
    "像是": "Seems like ",  # placeholder removal guard
    "液态记忆": "Liquid Memory",
    "弥散印象": "Diffuse Impression",
    "坚实聚合物": "Solid Aggregate",
    "普通聚合物": "Plain Aggregate",
    "意识边界": "Mind Boundary",
    # ---- 图鉴与统计 ----
    "意识体": "Consciousness",
    "显化物": "Manifestations",
    "异常地点": "Anomaly Sites",
    "详情": "Details",
    "尚未解锁此分类中的可观测资料。": "No unlocked entries in this category yet.",
    "暂无描述。": "No description yet.",
    "记录": "Record",
    "遭遇": "Met",
    "解决": "Solved",
    "交互": "Talks",
    "未知": "Unknown",
    "此分类暂无条目。": "No entries in this category.",
    "异象层级": "Kind",
    "完整度": "Integrity",
    "移动速度": "Move Time",
    "攻击速度": "Attack Speed",
    "主要创伤": "Trauma",
    "观测范围": "Vision",
    "传递目击": "Relays Sightings",
    "崩解推进": "Dissolution Push",
    "可能遗留": "Possible Drop",
    "已观测遗留": "Observed Drops",
    "显化类别": "Category",
    "作用": "Effect",
    "承载位": "Slot",
    "单格叠放": "Stack",
    "效力": "Power",
    "弹体构想": "Projectile",
    "穿透": "Pierce",
    "推动": "Push",
    "爆发范围": "Blast",
    "可能形成": "May Form",
    "回合": " rounds",
    # ---- 征兆的「层」（使用次数，不随时间消失）----
    "层": " layers",
    "\u3000·\u3000": "  ·  ",
    # ---- 拾取面板 ----
    "共 {n} 件": "{n} items",
    "空格勾选 · A 全选 · Enter 捡起 · Esc/Q 关闭": "Space select · A select all · Enter pick up · Esc/Q close",
    "这里没有可拾取的显化物。": "Nothing here can be picked up.",
    "第 {a}-{b}/{c} 件 · 滚轮或 ↑↓ 滚动": "Items {a}-{b}/{c} · wheel or ↑↓ to scroll",
    "已选 {n} 件 · ": "{n} selected · ",
    "行囊 {a}/{b}": "Bag {a}/{b}",
    "没有选中任何显化物。": "Nothing selected.",
    "拾取：{items}。": "Picked up: {items}.",
    "拾取 {items}；背包已满，其余留在原地。": "Picked up {items}; bag is full, the rest stay on the ground.",
    "（{n} 回合）": " ({n} rounds)",
    "（{n}/{capacity}）": " ({n}/{capacity})",
    "拾取 {items}；先决定新记忆的去留。":
        "Picked up {items}; first decide what to do with the new memory.",
    "先决定待收纳记忆碎片的去留。":
        "First decide what to do with the pending memory fragment.",
    "已解决；主要创伤：": "Solved; main trauma: ",
    "。": ".",
    "你把它拾进了行囊。": "You picked it up into your bag.",
    # ---- 设置 ----
    "表征模式": "Symbol Mode",
    "切换主题符号与固定双列 ASCII 符号。": "Switch between themed glyphs and fixed two-column ASCII.",
    "主题符号": "Themed",
    "自动收纳": "Auto Pickup",
    "安全时进入显化物所在格后自动收纳。": "Auto-collect manifestations you step on when safe.",
    "默认展开注释": "Expand Notes",
    "控制行囊、观测录和操作页的灰色说明。": "Controls grey notes in bag, codex and action pages.",
    "语言": "Language",
    "切换界面与内容的显示语言。": "Switch the display language of UI and content names.",
    "向上主键": "Up Key",
    "向下主键": "Down Key",
    "向左主键": "Left Key",
    "向右主键": "Right Key",
    "小键盘5等待": "Numpad 5 Wait",
    "开启后按小键盘 5 原地等待一回合；关闭则 5 无效，避免误触。": "When on, numpad 5 waits one turn in place; when off, 5 does nothing.",
    # 音频与画面特效设置（2026-09-20 补齐：此前英文模式下这几项显示中文原文）
    "音效": "Sound Effects",
    "移动、投掷、下潜等动作音效。": "Action sounds for moving, throwing and descending.",
    "音效音量": "SFX Volume",
    "0 静音，10 最响。": "0 is silent, 10 is loudest.",
    "音乐音量": "Music Volume",
    "音乐": "Music",
    "背景音乐音量；0 为静音，不影响音效。": "Background music volume; 0 mutes music without affecting sound effects.",
    "播放主页、区域、梦中梦与结局音乐；与音效开关独立。": "Play menu, region, dream realm and ending music; independent of sound effects.",
    "背景音乐音量（音乐功能接入后生效）。": "Background music volume (effective once music is wired in).",
    "世界直写失败，已回退 Textual 渲染。": "World painter failed; Textual rendering restored.",
    "扫描线效果": "Scanlines",
    "低清醒度时的隔行扫描线（CRT 暗线）。可独立于画面特效开关。": "Interlaced scanlines at low lucidity (CRT dark lines); independent of the FX switch.",
    "画面特效": "Visual FX",
    "地图动态光影：关闭 / 流畅（10 帧） / 完整（呼吸光环·暗角·涟漪）。": "Map dynamic lighting: off / smooth (10 fps) / full (breathing halo, vignette, ripples).",
    "上下层切换动画": "Floor Transition Animation",
    "下潜/上浮时旧层崩解、新层在角色周围生成；关闭则直接切换。": "On descend/ascent, the old floor collapses and the new one forms around the character; disable for an instant switch.",
    "光照覆盖墙体": "Light Covers Walls",
    "动态光照作用于地板、墙体与一切格子；关闭则只照亮可通行的格。": "Dynamic lighting affects floors, walls and every cell; disable to light only walkable cells.",
    "命中定格": "Hit Stop",
    "命中后抖动与跳字短暂停在命中帧（40–70ms，0 关闭）；"
    "输入、回合结算与音效照常推进。":
        "Freeze the shake and the damage number on the impact frame for 40-70ms "
        "(0 turns it off); input, turn resolution and sound effects never wait.",
    "减少动态效果": "Reduce Motion",
    "关闭命中抖动与跳字上冲，保留伤害数字与命中格强调。":
        "Turn off screen shake and the rising damage number; the number itself and "
        "the hit-cell highlight stay on.",
    "平滑移动": "Smooth Movement",
    "图像地图中对连续移动进行显示插值；不改变回合结算，字符模式与减少动态效果下不生效。":
        "Interpolate continuous movement in image maps without changing turn resolution; "
        "inactive in character mode and with Reduce Motion enabled.",
    "Kitty 图像协议（实验）": "Kitty Graphics (Experimental)",
    "实验性：终端支持 Kitty 图形协议时改用 APC 传图，可能提高图像刷新上限。"
    "Windows 的 ConPTY 会丢弃该序列，将自动回退现有图像通道；开启后如画面异常请关闭。":
        "Experimental: send images through the Kitty graphics APC when the terminal "
        "supports it, which may raise the image refresh ceiling. Windows ConPTY drops "
        "this sequence, so it falls back to the existing image channel; turn it off "
        "if the map looks wrong.",
    "字符高刷模式（实验）": "Character High-Refresh (Experimental)",
    "实验性：强制字符地图并启用低开销文本帧，省掉图像编码与"
    "逐格图像准备。字符地图按行动步进，30Hz 采样只服务动画与"
    "特效，不做像素级插值；默认关闭。":
        "Experimental: force the character map and use a low-cost text frame that "
        "skips image encoding and per-cell image preparation. The character map "
        "advances per action; 30Hz sampling only serves animation and effects, with "
        "no pixel-level interpolation. Off by default.",
    "左侧事件记录": "Left Event Log",
    "在地图左下叠加透明事件记录；开启后右侧默认页改为行囊。":
        "Overlay a transparent event log on the map's bottom left; "
        "the right pane then opens on the bag by default.",
    # 层植物总览 / 格子详情（core/plant_survey）
    "本层植物 {total} 株（{body}）": "Layer flora: {total} ({body})",
    "高 {n}": "{n} tall",
    "{label} {n}": "{label} {n}",
    "已耗尽 {n}": "{n} spent",
    "全部完好": "all intact",
    "可吸": "absorb", "可搬": "push", "可净": "purify", "可炸": "ignite",
    "可电": "shock", "可削": "damage", "可放气": "release gas",
    "可放液": "release liquid", "可缠": "snare",
    "当前格": "Here",
    "点击查看": "click for details",
    "格": "tiles",
    "遮蔽气/高丛": "obscuring gas/tall cover",
    "通电": "powered",
    "可燃液体": "flammable liquid",
    "无（无对应弱点）": "None (no matching weakness)",
    "视野内没有墙体固体。": "No wall solids in sight.",
    "少字模式": "Terse Mode",
    "右侧栏尽量用符号和英文缩写代替文字：状态、地形、页签、子菜单与"
    "环境页都只留图标；左侧窗口和全屏窗口不受影响，可展开注释默认收起。":
        "Use symbols and short English abbreviations in the right pane (status, terrain, "
        "tabs, submenus and environment page); left overlay and full-screen windows keep "
        "their text, and expandable notes start collapsed.",
    "异象切换提示": "Anomaly Intent Hints",
    "异象开始怀疑、追踪、逃离、蓄力、被打断或进入恢复时，"
    "在该格短暂亮起角标；关闭不影响技能危险区域与观察文字。":
        "Briefly badge the cell when an anomaly starts suspecting, chasing, fleeing, "
        "charging, gets interrupted or enters recovery; danger zones and observe text stay on.",
    "异象整格意图高亮": "Anomaly Cell Intent Highlight",
    "开启后异象切换意图时，在角色地图给异象所在整格字形叠前景高亮；"
    "默认关闭，避免大标记周期性重绘影响连续移动。右上角小角标不受影响。":
        "When on, highlight the whole anomaly glyph cell in character mode on intent "
        "switches; off by default to avoid periodic full-cell redraws. Corner badge is separate.",
    # 统一发射源／弹匣／换弹（2026-10-21）
    "材料来源待选": "Material source pending",
    "容器无对应材料": "No matching material in container",
    "想象{cost}": "Imagination {cost}",
    "空匣": "Empty",
    "换弹 {done}/{total} · 已付{cost}想象": "Reload {done}/{total} · paid {cost} imagination",
    "想象不足：需{cost} · 换弹{steps}行动": "Not enough imagination: {cost} · reload {steps} action(s)",
    "R换弹 {cost}想象/{steps}行动": "R reload {cost} imagination / {steps} action(s)",
    "‹换源›": "‹Source›",
    "R换弹（先选武器）": "R reload (pick weapon)",
    "O锁定": "O lock",
    "O换敌": "O target",
    "鼠标左键": "Left click",
    "Esc退出": "Esc exit",
    "选择换弹武器": "Choose Weapon to Reload",
    "待选目标判定": "target check pending",
    "瞄准；瞄准中再按打开来源表": "Aim; press again while aiming for the source list",
    "为当前发射源换弹；有未完成换弹则继续；空匣/费用不足零消耗":
        "Reload the current source; continue an unfinished reload; empty or unaffordable is free",
    "没有其他可选来源。": "No other source available.",
    "锁定目标不在新来源射程内，已改为自由落点。":
        "The locked target is out of the new source's range; switched to free aim.",
    "这个一次性来源已经失效。": "That one-shot source is no longer valid.",
    "基础发射（旧档继承）": "Basic Fire (legacy inheritance)",
    "提供发射来源": "Provides a firing source",
    "装备后这件武器可作为发射来源；卸下即不再提供。":
        "While equipped this weapon is a firing source; unequipping removes it.",
    "消耗基础发射 1 发": "Uses 1 basic-fire round",
    "旧档继承的基础发射已经用完，请先换弹。":
        "The inherited basic fire is empty; reload it first.",
    "聚合弹库存不足。": "Not enough aggregate rounds.",
    "「解锁发射」命令已随统一发射源移除，旧回放与旧脚本不能继续改变世界。":
        "The 'unlock fire' command was removed with unified firing sources; old replays "
        "and scripts can no longer change the world.",
    "发射来源已经统一：可用来源可以自由切换，无限来源改为逐武器弹匣并需要付费换弹，U 键不再解锁发射。"
    "旧档的永久发射许可已继承为独立来源「基础发射（旧档继承）」：容量 3，换弹 2 行动／3 想象；"
    "它不会让其他武器获得无限库存。聚合弹数量原样保留；迁移前梦痕已备份。":
        "Firing sources are now unified: available sources can be switched freely, infinite "
        "sources use per-weapon magazines with paid reloads, and U no longer unlocks firing. "
        "The old permanent license was inherited as the independent source 'Basic Fire "
        "(legacy inheritance)': capacity 3, reload 2 actions / 3 imagination; it does not "
        "grant other weapons unlimited ammo. Aggregate rounds are kept as-is; the pre-migration "
        "save was backed up.",
    "发射来源已经统一：可用来源可以自由切换，无限来源改为逐武器弹匣并需要付费换弹，U 键不再解锁发射。"
    "本次未发现可继承的永久发射许可（或旧许可只来自盘面装备），因此只按真实装备与聚合弹生成来源；"
    "旧结构无法可靠区分历史付费与装备许可，未额外赠送能力。物品、联想盘与构想原样保留；迁移前梦痕已备份。":
        "Firing sources are now unified: available sources can be switched freely, infinite "
        "sources use per-weapon magazines with paid reloads, and U no longer unlocks firing. "
        "No inheritable permanent license was found (or it came only from equipped board pieces), "
        "so sources come only from real equipment and aggregate rounds; the old structure cannot "
        "reliably separate past payments from equipment licenses, so nothing extra is granted. "
        "Items, the association board and constructs are kept as-is; the pre-migration save was "
        "backed up.",
    "流畅": "Smooth",
    "完整": "Full",
    "开启": "On",
    "关闭": "Off",
    "设置已保存。": "Settings saved.",
    "设置仅本次会话生效；配置文件暂时无法写入。": "Settings apply to this session only; the config file could not be written.",
    "设置没有变化。": "Setting unchanged.",
    "等待按键...": "Press a key...",
    "↑↓ 选择 · ←→ 调整 · Enter/Space 修改 · Q 返回": "↑↓ choose · ←→ adjust · Enter/Space change · Q back",
    "等待输入新的": "Press the new key for ",
    "；Q 或 Esc 取消。": "; Q or Esc to cancel.",
    "已取消按键捕获。": "Key capture cancelled.",
    # ---- 异象 ----
    "纸页犬": "Page Hound",
    "折页人": "Folded Person",
    "倒放鼓手": "Reverse Drummer",
    "模型搬运工": "Model Porter",
    "无声观众": "Silent Audience",
    "冷却人偶": "Cooling Doll",
    "逆光读者": "Backlit Reader",
    "回声门": "Echo Door",
    "游荡的纸页犬": "Wandering Page Hound",
    "强烈异象·无脸编辑": "Elite·Faceless Editor",
    "强烈异象·房间折叠体": "Elite·Folded Room",
    "核心执念·未完成句号": "Core·Unfinished Period",
    "挂钟守夜人": "Clock Keeper",
    "镜像侍者": "Mirror Attendant",
    "纸鱼": "Paper Fish",
    "梦游裁缝": "Sleepwalking Tailor",
    "人形衣架": "Human Coat Rack",
    "楼梯回声": "Stair Echo",
    "强烈异象·双重曝光": "Elite·Double Exposure",
    "强烈异象·湿透的合唱团": "Elite·Soaked Choir",
    "强烈异象·迁徙的楼梯": "Elite·Migrating Staircase",
    "核心执念·空心的灯塔": "Core·Hollow Lighthouse",
    "残影": "Afterimage",
    "普通异象": "Ordinary Anomaly",
    "强烈异象": "Elite Anomaly",
    "核心执念": "Core Obsession",
    # 稀有度档位（目录/物品/事件通用标签）。
    "常见": "Common", "少见": "Uncommon", "稀有": "Rare", "非常稀有": "Very Rare",
    # 关系与立场（world/relations、结算、日志通用）。
    "中立": "Neutral", "和解中": "Reconciling", "敌对": "Hostile", "脱离": "Disengaged",
    # NPC 行为类型（交易/结局通用）。
    "囤积型": "Hoarder", "杀伐型": "Slayer", "直面型": "Confronter", "纵火型": "Arsonist",
    # 读唇意图（悬停）。
    "向你扑来": "lunging at you", "正在犹豫": "hesitating", "尚未察觉你": "unaware of you",
    "徘徊": "prowling",
    # 面板数值字段标签（ui/panel_fields LABEL_FIELDS 里此前漏翻的 12 个）。
    "悬停": "Hover", "基础值": "Base", "容量": "Capacity", "次数": "Uses",
    "持续": "Duration", "蓄势": "Windup", "费用": "Cost", "范围": "Area",
    "面积": "Footprint", "半径": "Radius", "目标数": "Targets", "声径": "Sound reach",
    # 图鉴字段标签（catalog_registry STAT_REGISTRY 里此前漏翻的 9 个）。
    "主动技能": "Active Skill", "稀有度": "Rarity", "最早主梦层": "Earliest Main-dream Depth",
    "每局最多获得": "Max per Run", "获取来源": "Obtained From",
    "材料甲": "Material A", "材料乙": "Material B",
    "产物": "Product", "产物形态": "Product Form",
    # 侧栏管理页数值标签。
    "推力": "Push", "爆炸半径": "Blast Radius",
    "心智创伤": "Mind Trauma",
    "清醒创伤": "Lucidity Trauma",
    "失控意识": "Stray Consciousness",
    "稳定意识": "Stable Consciousness",
    "受控意识": "Controlled Consciousness",
    "是": "Yes",
    "否": "No",
    # ---- 墙体 ----
    "压实聚合墙": "Compacted Aggregate Wall",
    "玻璃幕墙": "Glass Curtain Wall",
    "反光玻璃墙": "Reflective Glass Wall",
    "吸声聚合墙": "Sound-absorbing Wall",
    "冷凝囊壁": "Condensing Cyst Wall",
    "不稳定燃料墙": "Unstable Fuel Wall",
    "潮解纸墙": "Deliquescent Paper Wall",
    "蜡化记忆墙": "Waxed Memory Wall",
    "尖啸瓷墙": "Shrieking Porcelain Wall",
    "空心积木墙": "Hollow Blocks Wall",
    "活字字模墙": "Movable Type Wall",
    "记忆容器": "Memory Vessel",
    "思绪容器": "Thought Vessel",
    "门": "Door",
    "坚硬聚合墙": "Hardened Aggregate",
    "清醒石": "Clarity Stone",
    "梦晶簇": "Dream Crystal Cluster",
    "烛泪柱": "Candle Tear Pillar",
    "枕木": "Sleepers",
    "云块": "Cloud Block",
    "黄粱米堆": "Millet Mound",
    "灰烬": "Ash",
    # ---- 液体 ----
    "水": "Water",
    "红酒": "Red Wine",
    "黑墨": "Black Ink",
    "导电液态记忆": "Conductive Liquid Memory",
    "镇静溶液": "Sedative Solution",
    "燃油": "Fuel Oil",
    "酸蚀液": "Acid Etch",
    "纸浆": "Paper Pulp",
    "显影液": "Developer Fluid",
    "稀释记忆": "Diluted Memory",
    "泪滴溶液": "Tear Solution",
    "忘川水": "Lethe Water",
    "流动月光": "Flowing Moonlight",
    "熔化的时间": "Molten Time",
    "彩虹牛奶": "Rainbow Milk",
    "灵视之血": "Blood of True Sight",
    "蜂蜜": "Honey",
    "以太": "Aether",
    "熔融蜡烛": "Molten Wax",
    # ---- 气体 ----
    "水蒸气": "Steam",
    "黑烟": "Black Smoke",
    "毒气": "Poison Gas",
    "麻醉雾": "Anesthetic Fog",
    "酒气": "Alcohol Fumes",
    "遮蔽弥散印象": "Obscuring Impression",
    "可燃气体": "Flammable Gas",
    "灰尘云": "Dust Cloud",
    "回声雾": "Echo Fog",
    "灼热蒸汽": "Scalding Steam",
    "静电尘": "Static Dust",
    "催眠雾": "Hypnotic Fog",
    "清醒香气": "Clarity Aroma",
    "安眠香": "Sleep Incense",
    "褪黑素雾": "Melatonin Mist",
    "咖啡因气": "Caffeine Vapor",
    # ---- 征兆 ----
    "过电": "Charged",
    "镇静": "Calmed",
    "腐蚀": "Corroded",
    "迟滞": "Sluggish",
    "显影": "Developed",
    "温热": "Warmed",
    "回暖": "Tear-warmed",
    "润泽": "Moistened",
    "中毒": "Poisoned",
    "迟钝": "Sedated",
    "醉意": "Drunk",
    "酩酊": "Tipsy",
    "遮蔽": "Obscured",
    "可燃": "Volatile",
    "呛尘": "Dusty",
    "回声": "Echoing",
    "灼伤": "Scalded",
    "麻痹": "Numb",
    "深眠": "Deep Sleep",
    "过热余波": "Overclock Aftermath",
    "迟滞沉积": "Viscous Debt",
    "双重成像": "Double Exposure",
    "无痕步": "Traceless Step",
    "液面滑行": "Liquid Glide",
    "镜面架势": "Mirror Stance",
    "挂载替身": "Hung Stand-in",
    "透镜余晖": "Lens Afterglow",
    "照彻": "Illumination",
    "遗忘": "Forgetting",
    "放大": "Enlarged",
    "诅咒灵视": "Cursed Sight",
    "月下": "Moonlit",
    "蜜裹": "Honeyed",
    "时间熔化": "Time-melted",
    "清朗": "Clear-headed",
    "安眠": "Poppy Sleep",
    "褪黑": "Melatonin",
    "咖啡因": "Caffeinated",
    "正面": "Positive",
    "负面": "Negative",
    "中性": "Neutral",
    # ---- 物品 ----
    "小型回声发射器": "Small Echo Emitter",
    "折线投影仪": "Line Projector",
    "冲击折页": "Impact Fold",
    "火柴的蓝端": "Blue End of the Match",
    "电池的背面": "Back of the Battery",
    "半罐温咖啡": "Half Can of Warm Coffee",
    "折叠弹影": "Folded Projectile Shadow",
    "旧耳机的线圈": "Coil of Old Headphones",
    "雨夜的机械声": "Machinery of a Rainy Night",
    "未完成的批注": "Unfinished Annotation",
    "模型盒里多出的螺丝": "Extra Screw from the Model Box",
    "没有日期的车票": "Dateless Ticket",
    "没有标签的镇静剂": "Unlabeled Sedative",
    "一小片清醒玻璃": "A Shard of Clear Glass",
    "脱落的键帽": "Fallen Keycap",
    "收音机里的雨": "Rain from the Radio",
    "模型房间的灯": "Lamp of the Model Room",
    "没有结尾的歌": "Song without an Ending",
    "草稿边缘的折痕": "Crease on the Draft Margin",
    "塑料齿轮的午后": "Afternoon of Plastic Gears",
    "弯曲的挂钩": "Bent Hook",
    "单边耳机": "Single Earphone",
    "破损的怀表": "Broken Pocket Watch",
    "灯塔透镜": "Lighthouse Lens",
    "楼梯铆钉": "Stair Bolt",
    "卷尺": "Tape Measure",
    "受潮的乐谱页": "Damp Score Page",
    "阁楼的灰尘": "Attic Dust",
    "盐渍的护目片": "Salted Goggle Lens",
    "干涸的手套": "Parched Gloves",
    "火燎的旧疤": "Old Burn Scar",
    "铅沉的骨髓": "Lead-Heavy Marrow",
    "走路的惯性": "Gait Habit",
    "撑开的肺叶": "Broadened Lung",
    "平稳的脉搏": "Steady Pulse",
    "深埋的储备": "Deep Reserve",
    "凉的半罐茶": "Cold Half Can of Tea",
    "过期的糖衣药丸": "Expired Sugar Pill",
    "浓缩咖啡因": "Espresso Shot",
    "温水": "Warm Water",
    "汽笛": "Whistle",
    "闪光灯泡": "Flash Bulb",
    "肥皂片": "Soap Sliver",
    "保温杯的余热": "Thermos Residue",
    "发条半卷": "Half-wound Spring",
    "弹簧折叠件": "Coiled Spring",
    "镜面碎片": "Mirror Shard",
    "湿折页": "Wet Fold",
    "空心的台阶": "Hollow Step",
    "双重曝光底片": "Double-exposure Negative",
    "松脱的缝线": "Loose Thread",
    "携带意象": "Carried Image",
    # 图鉴/导航按钮：分类名在按钮上空间紧张，用短名 "Carried"，条目详情仍用全称。
    "携带": "Carry",
    "摄入物": "Ingestible",
    "易逝物": "Perishable",
    "惯用物": "Habit Tool",
    "记忆碎片": "Memory Fragment",
    "交互道具": "Interactive Tool",
    "手中意象": "Hand Image",
    "自我表层": "Self Surface",
    "依附物": "Attachment",
    "依附物·一": "Attachment I",
    "依附物·二": "Attachment II",
    # ---- 事件 ----
    "桌上的咖啡环": "Coffee Ring on the Desk",
    "缺少一颗螺丝的模型": "Model Missing One Screw",
    "无人检票的站台": "Unticketed Platform",
    "玻璃里的第二个房间": "Second Room in the Glass",
    "收音机的雨声": "Rain on the Radio",
    "模型房间的灯": "Lamp of the Model Room",
    "空白乐谱": "Blank Score",
    "编辑留下的批注": "Editor's Annotation",
    "齿轮停下的午后": "Afternoon the Gear Stopped",
    "灰烬下的打火机": "Lighter under the Ash",
    "浴缸里的退潮": "Ebb in the Bathtub",
    "药盒的最后一格": "Last Slot of the Pill Box",
    "晕开的休止符": "Blurred Rest Note",
    "阁楼的折叠梯": "Folding Ladder to the Attic",
    "末班车的窗": "Window of the Last Train",
    "静电里的电台": "Radio in the Static",
    "卷尺画出的房间的界线": "Room Line Drawn by the Tape",
    # ---- 洞察 ----
    "路线依赖": "Route Dependence",
    "机械迷恋": "Machine Fondness",
    "延迟抵达": "Delayed Arrival",
    "透明边界": "Transparent Boundary",
    "噪声耐受": "Noise Tolerance",
    "局部照明": "Local Lighting",
    "留白": "Blank Space",
    "现实洞察": "Reality Insight",
    "灰烬记忆": "Ash Memory",
    "深层耐性": "Deep Tolerance",
    "液态亲和": "Liquid Affinity",
    "双读": "Double Reading",
    "和声耐受": "Harmony Tolerance",
    "残影直觉": "Afterimage Instinct",
    "疾行拾荒": "Scavenger's Stride",
    "抗辐射体质": "Radiation Hardened",
    "冷韧": "Cold-Bound",
    "抗灼": "Scald-Proof",
    "镜术精通": "Mirror Mastery",
    "蜜脉": "Honey Vein",
    "灯塔共鸣": "Lighthouse Resonance",
    "水银": "Mercury",
    "液氮": "Liquid Nitrogen",
    "超临界流体": "Supercritical Fluid",
    "沉重": "Leaden",
    "冻僵": "Frozen",
    "剥蚀": "Eroding",
    "辐射病": "Radiation Sickness",
    "酒精蒸气": "Alcohol Vapor",
    "辐射尘埃": "Radiation Dust",
    "铅板": "Lead Plate",
    "盐晶壁": "Salt Crystal Wall",
    "木桌子": "Wooden Table",
    "石台": "Stone Platform",
    # ---- 无意识领域（21–27）名字 ----
    "赤致密聚合墙": "Crimson Dense Polymer",
    "黄致密聚合墙": "Amber Dense Polymer",
    "蓝致密聚合墙": "Azure Dense Polymer",
    "绿致密聚合墙": "Viridian Dense Polymer",
    "梦魇岩": "Nightmare Rock",
    "呜咽晶柱": "Weeping Crystal",
    "沉思铁幕": "Iron Curtain of Thought",
    "无光绒墙": "Lightless Velvet",
    "蚀梦菌毯": "Dream-Eating Mold",
    "静默碑岩": "Silent Stele",
    "无意识结晶": "Unconscious Crystal",
    "悔恨之锚": "Anchor of Regret",
    "千层叠岩": "Thousand-Strata Rock",
    "回响黑曜岩": "Echoing Obsidian",
    "无念黑渊": "Abyss of No-Thought",
    "熔念金属": "Molten Ideation",
    "静滞之泪": "Still Tears",
    "星辉露": "Starlight Dew",
    "噩梦纤维": "Nightmare Fiber",
    "原初混沌": "Primordial Chaos",
    "呢喃": "The Murmur",
    "虚无孢子": "Void Spores",
    "溶梦酸雾": "Dream-Dissolving Acid",
    "噩梦气息": "Nightmare Breath",
    "晨霜清气": "Morning Frost Air",
    "曼德拉草": "Mandrake",
    "曼陀罗": "Datura",
    "冥河柳": "Styx Willow",
    "夜皇后": "Queen of the Night",
    "缚魂藤": "Soul-Binding Vine",
    "贤者之苔": "Sage's Moss",
    "镜面兰": "Mirror Orchid",
    "千梦铃兰": "Thousand-Dream Lily",
    "无意识沉钟": "Sunken Bell of the Unconscious",
    "缄默映像": "Silent Mirror-Image",
    "噬念蠕虫": "Thought-Devouring Worm",
    "无面守夜人": "Faceless Watchman",
    "强烈异象·噩梦编织者": "Powerful Anomaly · Nightmare Weaver",
    "强烈异象·遗忘织者": "Powerful Anomaly · The Forgetter",
    "强烈异象·空白裂隙": "Powerful Anomaly · Blank Rift",
    "强烈异象·原初冲动": "Powerful Anomaly · Primordial Impulse",
    "核心执念·初啼之核": "Core Obsession · The First Cry",
    "初啼之牙": "Fang of the First Cry",
    "无光斗篷": "Lightless Cloak",
    "虚空吊坠": "Void Pendant",
    "命运硬币": "Coin of Fate",
    "深念凿子": "Deep-Thought Chisel",
    "裂缝蜡印": "Rift Wax Seal",
    "织梦手套": "Dreamweaver Gloves",
    "迅念指环": "Ring of Swift Thought",
    "晨露药剂": "Morning Dew Potion",
    "深念茶": "Deep-Thought Tea",
    "虚空阻凝剂": "Void Coagulant",
    "无光灯笼": "Lightless Lantern",
    "灯塔的余烬": "Embers of the Hollow Lighthouse",
    "未竟的句点": "The Unfinished Full Stop",
    "初啼的余温": "Lingering Warmth of the First Cry",
    "薄荷露": "Mint Dew",
    "彩玻碎片": "Glass Shard",
    "贤者之粉": "Sage Powder",
    "千梦铃": "Dream Bell",
    "初啼的回声": "Echo of the First Cry",
    "沉入无意识的钟": "The Bell Sunken into Unconsciousness",
    "被遗忘的画廊": "The Forgotten Gallery",
    "名字的潮汐": "Tide of Names",
    "浅层梦境": "Shallow Dream",
    "幻觉空间": "Hallucination Space",
    "无意识领域": "The Unconscious Realm",
    "噩梦": "Nightmare",
    "失忆": "Amnesia",
    "灼念": "Burning Thought",
    "时滞": "Stillness",
    "星辉": "Starlit",
    "忘忧": "Worry-Free",
    "混沌冲刷": "Chaos Wash",
    "呢喃": "The Murmur",
    "虚无": "Voidness",
    "溶梦": "Dream-Dissolving",
    "晨霜": "Morning Frost",
    "幻觉安眠": "Hallucinated Sleep",
    "冥河之重": "Weight of the Styx",
    "月下": "Moonlit",
    "缚魂": "Soul-Bound",
    "初啼共鸣": "First-Cry Resonance",
    "静默惯习": "Habit of Silence",
    "听声辨向": "Sound Bearing",
    "借声藏步": "Borrowed Footfalls",
    "无意识领域尽头——初啼之渊——没有更深的入口。": "The end of the Unconscious Realm — the Abyss of the First Cry — has no deeper entrance.",
    "虚空被凝固回原处：噩梦、虚无与遗忘都散了。": "The void sets solid again: nightmare, voidness and oblivion disperse.",
    "你身上没有需要凝固的东西。": "Nothing on you needs setting.",
    "无光处亮起一片：{count} 格地形被永久显影。": "Light blooms in the dark: {count} tiles are permanently developed.",
    "曼德拉草发出尖啸：心智 +5，清醒度 −2。": "The mandrake shrieks: mind +5, lucidity −2.",
    "贤者之苔化作金色粉末：想象力 +8。": "The sage's moss turns to golden powder: imagination +8.",
    "镜面兰的花瓣立成一面镜子：下一次指向你的打击将被退回。": "The mirror orchid's petals rise into a mirror: the next strike aimed at you is reflected back.",
    "区域与深度": "Region & depth",
    "混沌": "Chaos",
    "呢喃吸入": "murmur inhalation",
    "虚无吸入": "void inhalation",
    "溶梦吸入": "dream-acid inhalation",
    "噩梦吸入": "nightmare inhalation",
    "晨霜吸入": "morning-frost inhalation",
    "健康": "Healthy",
    "受损": "Impaired",
    "危险": "Critical",
    "紧急": "Urgent",
    # ---- 2026-10-15 混乱化改造：心理分档跨档横幅（state._announce_tier_drop /
    # materials_sim._psyche_suffix）。【】是全角括号、属排版符号，不在
    # test_i18n_coverage 的 CJK 汉字区间内；{axis} 由调用方手动 .format 填入。
    "【{axis}·受损：环境开始不稳】": "【{axis}·Impaired: the environment starts to stir】",
    "【{axis}·危险：效果开始失控】": "【{axis}·Critical: effects begin to run wild】",
    "【{axis}·紧急：梦境彻底失控！】": "【{axis}·Urgent: the dream is completely out of control!】",
    "【梦境·危险：效果开始失控】": "【Dream·Critical: effects begin to run wild】",
    "【梦境·紧急：彻底失控！】": "【Dream·Urgent: total meltdown!】",
    "薄荷锭": "Mint Lozenge",
    "特浓薄荷茶": "Strong Mint Tea",
    "特浓薄荷茶": "Strong Mint Tea",
    "振奋": "Invigorated",
    "特浓薄荷茶提神醒脑：持续期间每 2 回合恢复 1 点清醒度。": "Sharpens the mind: while active, restores 1 lucidity every 2 rounds.",
    "使用特浓薄荷茶": "Drink Strong Mint Tea",
    "入口冰凉，瞬间压住眩晕。恢复少量清醒度。": "Ice-cold and instantly grounding. Restores a little lucidity.",
    "神志清醒，眩晕尽散。": "Mind clear, dizziness gone.",
    "视野中": "in sight",
    "第 10 层": "Layer 10",
    "第 20 层——梦的核心——没有更深的入口。": "Layer 20 — the Core of the Dream — has no deeper entrance.",
    # ---- 界面补全 ----
    "保存并退出": "Save & Quit",
    "返回/投掷": "Back / Throw",
    "本局": "Run",
    "硬": "H",
    "厚": "T",
    "完": "I",
    "存档栏": "Save Slots",
    "已选择存档槽 {n}。": "Selected slot {n}.",
    "终端尺寸不足，请扩大窗口后查看图鉴。": "Terminal too small — enlarge the window to view the codex.",
    "←→ 选择分类 · Enter 激活 · Q 返回主页": "←→ category · Enter open · Q home",
    "←→↑ 选择分类 · ↓/Enter 进入条目 · Q 返回主页": "←→↑ category · ↓/Enter open · Q home",
    "←→↑ 选择分类 · ↓/Enter 进入条目 · Q 返回菜单": "←→↑ category · ↓/Enter open · Q menu",
    "点击解锁": "Click to unlock",
    "当前没有可执行的解锁操作。": "No unlock action available.",
    "图鉴已全部解锁（新标记 {n} 条）。": "Codex fully unlocked ({n} newly marked).",
    " · 当前": " · current",
    "瞄准中：按任一方向键发射。": "Aiming: press any direction to fire.",
    "晶格被你推着滑了一格。": "The lattice slides one cell as you push.",
    "弹体陷进墙里，无声无息地消失了。": "The projectile sinks into the wall and vanishes without a sound.",
    "压电地板攒满了电荷，「啪」地放出一片电弧。": "The piezo floor reaches full charge and cracks out an arc.",
    "{event}：请选择回应方式。": "{event}: choose a response.",
    "没有正在进行的对话。": "No conversation is in progress.",
    "没有这个选项。": "No such option.",
    "你退出了{event}。": "You step away from the {event}.",
    "{event}：{choice}。{reward}{stats}": "{event}: {choice}. {reward}{stats}",
    "{event}：{choice}。{insight}{reward}{stats}": "{event}: {choice}. {insight}{reward}{stats}",
    "{event}：{choice}。{details}": "{event}: {choice}. {details}",
    "意识行囊已满，{event} 暂时无法交付显化物。": "The mind satchel is full; the {event} cannot hand over a manifestation for now.",
    "对话已经结束。": "The conversation has ended.",
    "事件：": "Event: ",
    "左键/数字/↑↓+Enter 选择 · 滚轮滚动 · Esc 离开": "Click/1-9/arrows+Enter choose · wheel scrolls · Esc leaves",
    "左键首击选中·再击确认 · 数字/Enter 亦可 · Esc 离开": "Click once to select, again to confirm · 1-9/Enter also work · Esc leaves",
    "　剩余触发次数 {n}": "  uses left: {n}",
    "交谈": "Talk",
    "{name}：「请讲。」": "{name}: \"Please, go ahead.\"",
    "你向{name}道别。": "You take your leave of the {name}.",
    "只是聊聊": "Just chat",
    "婉拒她的好意": "Politely decline",
    "「不了，谢谢。」": '"No, thank you."',
    "过一会再来": "Come back later",
    # ---- 稳定意识交易（2026-09-18 改版）：短标签 + 代价/所得两行 ----
    '交出消耗品，换一份洞察': 'Hand over consumables for an insight',
    '交出携带意象，换想象上限': 'Hand over carried images for imagination cap',
    '交出温咖啡，换清醒上限': 'Hand over warm coffee for lucidity cap',
    '付心智，换一件少见装备': 'Pay mind for an uncommon piece',
    '付清醒度，换一份洞察': 'Pay lucidity for an insight',
    '清醒换心智上限': 'Lucidity for mind cap',
    '心智换清醒上限': 'Mind for lucidity cap',
    '交出 2 件消耗品，换薄荷露': 'Hand over 2 consumables for Mint Dew',
    '付心智，换一份洞察': 'Pay mind for an insight',
    '付清醒度，换灯塔透镜': 'Pay lucidity for a Lighthouse Lens',
    '交出携带意象，换命运硬币': 'Hand over a carried image for a Coin of Fate',
    '付心智，买明示洞察': 'Pay mind for a named insight',
    '付心智，买随机洞察': 'Pay mind for a random insight',
    '交出消耗品，换螺丝刀': 'Hand over consumables for a Screwdriver',
    '交出折叠弹影，换蜡封图章': 'Hand over Folded Projectiles for a Wax Seal',
    '付清醒度，换晨露药剂': 'Pay lucidity for a Morning Dew Potion',
    '交出样本，换深念茶': 'Hand over samples for Deep-Thought Tea',
    '付清醒度，换多出的螺丝': 'Pay lucidity for a spare screw',
    '交出携带意象，换无光斗篷': 'Hand over carried images for a Lightless Cloak',
    '携带意象 ×{n}（含已装备）': '{n} carried image(s) (equipped included)',
    '消耗品或易逝物 ×{n}': '{n} consumable or fleeting item(s)',
    '洞察「{name}」': 'insight "{name}"',
    '随机洞察（事前不知道是哪条）': 'a random insight (unknown until received)',
    "代价 {cost}": "Cost: {cost}",
    "所得 {gain}": "Receive: {gain}",
    # ---- 稳定意识交易（2026-09-18 改版）：对话框、代价/所得、每位 NPC 的选项与台词 ----
    '代价：{cost} → 所得：{gain}': 'Cost: {cost} → You get: {gain}',
    '心智上限': 'mind cap',
    '清醒度上限': 'lucidity cap',
    '想象力上限': 'imagination cap',
    '{stat} −{n}': '{stat} −{n}',
    '{name}恢复完全': '{name} fully restored',
    '心智、清醒度与想象力全部恢复': 'Mind, lucidity and imagination are all fully restored',
    '随机交出 {n} 件携带意象（含已装备）': 'Hand over {n} random carried image(s) (equipped ones included)',
    '随机交出 {n} 件摄入物或易逝物': 'Hand over {n} random consumable(s) or fleeting item(s)',
    '获得 {item}': '{item}',
    '获得洞察「{name}」': 'insight "{name}"',
    '获得一个随机洞察（事前不知道是哪条）': 'Gain a random insight (you will not know which one)',
    '他翻了半天口袋，摊手：没有你还没见过的东西了。': 'He digs through his pockets and shrugs: there is nothing you have not already seen.',
    '交出任意的摄入物与易逝物各一件，换一份洞察': 'Hand over one consumable and one fleeting item for an insight',
    '交出三件携带意象，换想象力上限 +5': 'Hand over three carried images for imagination cap +5',
    '交两罐半罐温咖啡，换清醒度上限 +5': 'Hand over two half-cans of warm coffee for lucidity cap +5',
    '付 14 点心智，换一件少见装备（夜灯的电池）': 'Pay 14 mind for an uncommon piece (Night-light Battery)',
    '付 14 点清醒度，换一份洞察（局部照明）': 'Pay 14 lucidity for an insight (Local Lighting)',
    '以 12 点清醒度换心智上限 +6': 'Trade 12 lucidity for mind cap +6',
    '以 12 点心智换清醒度上限 +6': 'Trade 12 mind for lucidity cap +6',
    '交出三件摄入物或易逝物，换一瓶薄荷露': 'Hand over three consumables or fleeting items for a Mint Dew',
    '付 16 点心智，换一份洞察（延迟抵达）': 'Pay 16 mind for an insight (Delayed Arrival)',
    '付 16 点清醒度，换一副灯塔透镜': 'Pay 16 lucidity for a Lighthouse Lens',
    '交出一件随机携带意象，换一枚命运硬币': 'Hand over one random carried image for a Coin of Fate',
    '付 18 点心智，买一条说清了的消息（洞察「残影直觉」）': 'Pay 18 mind for a spelled-out lead (insight "Afterimage Instinct")',
    '付 12 点心智，买一条不知名的念头（随机洞察）': 'Pay 12 mind for an unnamed thought (random insight)',
    '交出两件摄入物或易逝物，换一把小号螺丝刀': 'Hand over two consumables or fleeting items for a Small Screwdriver',
    '交出两件折叠弹影，换一枚蜡封图章': 'Hand over two Folded Projectiles for a Wax Seal',
    '付 12 点清醒度，换一支晨露药剂': 'Pay 12 lucidity for a Morning Dew Potion',
    '交出样本（摄入物或易逝物 ×2），换深念茶': 'Hand over samples (2 consumables or fleeting items) for Deep-Thought Tea',
    '付 10 点清醒度，换一颗模型盒里多出的螺丝': 'Pay 10 lucidity for a Model-kit Spare Screw',
    '交出三件携带意象，换一件稀有装备（无光斗篷）': 'Hand over three carried images for a rare piece (Lightless Cloak)',
    '付 13 点心智，换一份洞察（疾行拾荒）': 'Pay 13 mind for an insight (Swift Scavenging)',
    '观测家转着黄铜镜筒打量你：「有意思……你的梦没有折痕。」': 'The observer turns a brass eyepiece over you: "Interesting... your dream has no creases."',
    '「拿点我没见过的东西来，我可以付『看得见的报酬』。」': '"Bring me something I have not seen, and I will pay in visible coin."',
    '「睡不着，还是醒不了？两种生意我都做。」': '"Cannot sleep, or cannot wake? I deal in both."',
    '「清醒一点，或者安稳一点——选一头，另一头归我。」': '"A little more lucid, or a little more settled — pick one, the other is mine."',
    '「呵，初次见面！做个小交易吧——拿你一件『亮闪闪的』，换我兜里的宝贝。」': '"Ha, first meeting! Let us make a small deal — one shiny thing of yours for a treasure of mine."',
    '「放心，魔鬼的契约从不撒谎，只是从不写全。」': '"Fear not: a devil\'s contract never lies. It simply never says everything."',
    '她把委托书摊在膝盖上：「下层的梦里有股味道，替我把样本带上来。」': 'She spreads the commission on her knees: "Something smells in the dream below. Bring me a sample."',
    '「报酬好商量。跑腿的规矩：先验货，后付账。」': '"The pay is negotiable. Errand rules: check the goods first, settle after."',
    "没有正在进行的对话。": "No conversation is in progress.",
    "心智不足。": "Not enough mind.",
    "清醒度不足。": "Not enough clarity.",
    "{item}不足。": "Not enough {item}.",
    "可支付的携带意象不足。": "Not enough carried images to pay with.",
    "摄入物/易逝物不足。": "Not enough ingestibles/perishables.",
    "想象力不足。": "Not enough imagination.",
    "摄入物/易逝物不足（要 {need} 件，只有 {owned} 件）。":
        "Not enough ingestibles/perishables (need {need}, have only {owned}).",
    "这项交易没有可交付的托盘。": "This trade has no tray to deliver into.",
    "托盘上的{kind}不足（要 {need}，只有 {held}）。":
        "Not enough {kind} on the tray (need {need}, have only {held}).",
    "意识行囊已满，装不下 {item}。": "Your satchel of mind is full — {item} will not fit.",
    "{stat}上限已经低到付不出这笔代价了。":
        "That {stat} cap is already too low to pay this cost.",
    "交付物已经不在了——重新把{req}备好再来。":
        "The deliverable is gone — prepare {req} again and come back.",
    "这份梦痕是旧版存档（格式 v{old}，当前 v{new}）：NPC 与世界事件的记账口径已经换掉，旧账目无法映射——请开一局新梦。":
        "This dream trace is an old save (format v{old}; current v{new}). The bookkeeping for NPCs and world "
        "events has changed and the old records cannot be mapped — please start a new dream.",
    # ---- 立场与责任归属（world/relations.py，重构方案 §4.4）----
    "对方": "the other party",
    "这个人已经不在这里了。": "That person is not here anymore.",
    "{name}对你没什么意见。": "{name} has nothing against you.",
    "{name}只是防着你手上那一下，没什么可解释的。":
        "{name} is only wary of what your hands do — there is nothing to explain.",
    "{name}在等你把条件付掉，不是听你说明。":
        "{name} is waiting for payment, not for another explanation.",
    "{name}还在当面追着你——先离开他的追责圈，等他冷静下来。":
        "{name} is still in your face about it — step out of their reach and let them cool down.",
    "{name}跟你没什么条件要谈。": "{name} has no terms to discuss with you.",
    "{name}还没跟你开出条件。": "{name} has not set terms with you yet.",
    "{name}还在气头上，现在出价只会被他当成挑衅。":
        "{name} is still furious; an offer now would read as provocation.",
    "条件已经开出来了——{name}在等的是付款，不是再谈一次。":
        "The terms are already on the table — {name} waits for payment, not more negotiating.",
    "火还在烧，{name}不肯靠近谈。先把危险源处理掉。":
        "The fire is still going; {name} won't come close to talk. Deal with the hazard first.",
    "{name}把手里的活放下，挡在工位前：「那边不能碰。再有一次我就得躲着你了。」":
        "{name} sets the work down and blocks the desk: \"Don't touch that. Once more and I'll have to keep my "
        "distance from you.\"",
    "{name}掂起了防身的东西，把门口让给你——这里的服务暂时关了。":
        "{name} weighs a makeshift weapon and clears the doorway — service here is closed for now.",
    "{name}倒下了。站着的人看见了这一幕，这一笔会被人记下。":
        "{name} has fallen. Anyone watching saw it, and this will be written down.",
    "{name}重新回到工位上，像打算把这页翻过去。":
        "{name} drifts back to work, as if to turn the page.",
    "{name}退回了自己的岗位，不再堵着门口。":
        "{name} retreats to their post and stops blocking the door.",
    "你解释了原委，{name}点了一下头：「这次算了。」":
        "You explain what happened, and {name} nods: \"Forget it this time.\"",
    "{name}开出了条件：交出 {amount} 点想象力作为补偿，这一页就翻掉。":
        "{name} names their terms: hand over {amount} imagination as compensation and the matter is closed.",
    "补偿已付清：{detail}。{name}把账合上了。":
        "Compensation paid: {detail}. {name} closes the ledger.",
    "对方挡在工位前，手里掂着东西——这里的服务暂时关了。":
        "They block the desk, something weighed in hand — service here is closed for now.",
    "对方不再拦着门口，但也没打算做生意：先解释清楚。":
        "They no longer block the door, but there is no trade either: explain yourself first.",
    "对方防着你手上的动作，买卖还是照做。":
        "They watch your hands, but business goes on as usual.",
    "「条件摆在那儿：付了才算翻篇。」": "The terms are on the table: pay them and the page turns.",
    "解释：那一下不是冲着你在做的": "Explain: that blow was not aimed at you",
    "提出补偿（把想象力交出来）": "Offer compensation (hand over imagination)",
    "按开出的条件付补偿": "Pay the compensation as agreed",
    "先离开，等对方冷静下来": "Step back and let them cool down",
    "结束对话": "End the conversation",
    "心智 −{n}": "mind −{n}",
    "清醒度 −{n}": "clarity −{n}",
    "想象力 −{n}": "imagination −{n}",
    "{liquid} ×{n}（从托盘扣除）": "{liquid} ×{n} (deducted from the tray)",
    "{stat}上限 −{n}": "{stat} cap −{n}",
    "{item} ×{n}": "{item} ×{n}",
    "交出 {item}": "handed over {item}",
    "交出 {item} ×{n}": "handed over {item} ×{n}",
    "交出 {item}（联想盘上的语句已拆开）":
        "handed over {item} (its clause taken apart on the association board)",
    "交付{kind} ×{n}": "delivered {kind} ×{n}",
    "托盘扣除{kind} ×{n}": "tray pays {kind} ×{n}",
    "获得 {item}。": "Gained {item}.",
    "心智恢复完全。": "Mind fully restored.",
    "清醒度恢复完全。": "Clarity fully restored.",
    "想象力恢复完全。": "Imagination fully restored.",
    "三项意识指标全部恢复。": "All three faculties fully restored.",
    "{stat} +{n}": "{stat} +{n}",
    "{name}：{choice}。{detail}": "{name}: {choice}. {detail}",
    "火焰舔过你的意识边缘（清醒 −1）。": "Flames lick at the edge of your mind (clarity −1).",
    "「{name}」被{label}燎到，慌忙躲开了。": "\"{name}\" is singed by the {label} and scrambles away.",
    "阀门的水把盆里的{kind}顶走了。": "The valve's water flushes the {kind} out of the basin.",
    "高浓度的气体轰然引爆！": "The dense gas detonates with a roar!",
    "{item}在远处轰然炸开。": "The {item} bursts apart in the distance.",
    "{item}在远处碎开，火焰四溅（点燃 {n} 格）。": "The {item} shatters in the distance, spraying fire ({n} cells lit).",
    "{item}在远处迸出火星（点燃 {n} 格）。": "The {item} sparks in the distance ({n} cells lit).",
    "火焰在身边四溅（点燃 {n} 格）。": "Fire sprays around you ({n} cells lit).",
    "火星在身边迸开（点燃 {n} 格）。": "Sparks burst around you ({n} cells lit).",
    "{item}在脚下轰然炸开。": "The {item} bursts apart at your feet.",
    "{item}在脚下碎开，火焰四溅（点燃 {n} 格）。": "The {item} shatters at your feet, spraying fire ({n} cells lit).",
    "{item}在脚下迸出火星（点燃 {n} 格）。": "The {item} sparks at your feet ({n} cells lit).",
    "引爆构想的火星找不到落点——视野内没有可燃的记忆。": "The detonation spark finds no target — no flammable material in sight.",
    "引爆构想的火星落在 ({x}, {y})。": "The detonation spark lands at ({x}, {y}).",
    "火墙构想燃起了 {n} 格火墙。": "The firewall concept raises {n} cells of flame.",
    "烈焰新星在你周围炸开。": "A flame nova bursts around you.",
    "测试模式": "Test Mode",
    "没有可释放的目标格（移动鼠标或用观察 ? 指定）。": "No target cell to release onto (move the mouse or aim the observe ?).",
    "征兆只能释放在自己或意识体所在的格子。": "Portents can only be released onto a cell occupied by you or another consciousness.",
    "调试：{name} 获得{portent}（{rounds} 回合）。": "Debug: {name} gains {portent} ({rounds} rounds).",
    "调试：在 ({x}, {y}) 释放了 {item}。": "Debug: released {item} at ({x}, {y}).",
    "调试：直接习得构想 {name}。": "Debug: ability {name} learned directly.",
    "调试：已清空全部洞察。": "Debug: all insights cleared.",
    "调试：已清空全部构想。": "Debug: all abilities cleared.",
    "调试：已清空全部征兆。": "Debug: all portents cleared.",
    "调试：已清空行囊。": "Debug: inventory cleared.",
    # ---- 调试面板·移动（2026-09-21：上下楼无视崩解度 + 传送到空地）----
    "传送": "Teleport",
    "调试：已选择 {item}，按 l 执行。": "Debug: selected {item}; press l to run it.",
    "调试：已{item}。": "Debug: {item} done.",
    "没有可传送的目标格（移动鼠标或用观察 ? 指定）。": "No target cell to teleport to (move the mouse or aim the observe ?).",
    "目标格 ({x}, {y}) 在地图之外，无法传送。": "Target cell ({x}, {y}) is outside the map — cannot teleport.",
    "目标格 ({x}, {y}) 是实心的，不是空地，无法传送。": "Target cell ({x}, {y}) is solid, not open ground — cannot teleport.",
    "目标格 ({x}, {y}) 已有意识体，无法传送。": "Target cell ({x}, {y}) already holds a consciousness — cannot teleport.",
    "调试：已传送至 ({x}, {y})。": "Debug: teleported to ({x}, {y}).",
    "已选择：{item}（{cat}）· 按 l 执行": "Selected: {item} ({cat}) · press l to run",
    # ---- 异象技能 v3（2026-09-22）----
    "{enemy}开始积蓄力量——快离开它的范围！": "{enemy} is gathering power — get out of its zone!",
    "冲击波扫过——{enemy}的震波命中了你！": "The shockwave sweeps through — {enemy}'s burst hits you!",
    "震波在范围外散开了——你躲开了。": "The shockwave disperses outside its zone — you dodged it.",
    "{enemy}的远程打击命中了你。": "{enemy}'s ranged strike hits you.",
    "它一连击中了 {n} 次。": "It lands {n} hits in a row.",
    # ---- 弹道动画与跳弹（2026-09-23）----
    "弹体从淀粉墙上弹了回来！": "The shot ricochets off the cornstarch wall!",
    "浅角掠过墙面——弹体跳弹了！": "Grazing the wall at a shallow angle — the shot ricochets!",
    "{enemy}朝你扔来一份会炸的东西——快离开落点！": "{enemy} lobs something explosive at you — clear the landing spot!",
    "{enemy}点起了火！": "{enemy} starts a fire!",
    "{enemy}凝出一圈寒霜，抽干了周围的气体与液体。": "{enemy} condenses a ring of frost, wicking away the surrounding gases and liquids.",
    "{enemy}的边缘爬上周围的墙——墙体正在剥落。": "{enemy}'s edge creeps onto the nearby walls — masonry is flaking away.",
    "{enemy}撞碎了挡路的墙！": "{enemy} smashes through the wall in its way!",
    # ---- 调试面板·自我增强 + 移动扩展（2026-09-22）----
    "调试：跳到梦中梦·{name} 第 {n} 层。": "Debug: jumped to dream-within-dream {name}, layer {n}.",
    "调试：跳到深层边界第 {n} 层。": "Debug: jumped to deep boundary layer {n}.",
    "调试：{item}已{state}。": "Debug: {item} {state}.",
    "调试：{item}（{n}）。": "Debug: {item} ({n}).",
    "前四项按 l 开/关（条目旁标注当前状态），后三项按 l 立即回满":
        "First four toggle with l (current state shown beside each entry); the last three refill instantly with l",
    "下潜/上浮无视崩解度 · 传送落 l 指向的空地（观察 ? 或鼠标光标），非法目标拒绝":
        "Descend/ascend ignore dissolution · teleport lands on the open ground pointed at by l "
        "(observe ? or mouse cursor); illegal targets are refused",
    "回合数": "Rounds",
    "层数": "Stacks",
    "（无层数，层数无效）": "(no stacks — stack setting ignored)",
    "分类": "Categories",
    "Tab/←→ 换列 · ↑↓/ws 移动": "Tab/arrows switch column · ↑↓/ws move",
    "清空洞察": "Clear insights",
    "清空构想": "Clear abilities",
    "清空征兆": "Clear portents",
    "清空行囊": "Clear inventory",
    "取消/关闭": "Cancel/Close",
    "Tab/←→ 换列 · ↑↓/wasd 移动": "Tab/arrows switch column · ↑↓/wasd move",
    "-/= 调整（回合 1–99 · 层 1–9） · l 放置": "-/= adjust (rounds 1–99 · stacks 1–9) · l place",
    "精致": "Refined",
    "已选择：{item}（{cat}）· l 在光标格释放": "Selected: {item} ({cat}) · l releases at cursor",
    "深层边界": "Deep Boundary",
    "深层边界 ·  回合数 {rounds}": "Deep Boundary · rounds {rounds}",
    "深层边界没有回头路——梦到这里只向前。": "The Deep Boundary has no way back — the dream only goes forward.",
    "你走进裂隙。下潜至深层边界。": "You step into the rift. You descend into the Deep Boundary.",
    "清醒不足，裂隙强行收拢——你承受了 {amount} 点心智创伤。": "Too little clarity — the rift slams shut, dealing {amount} mind damage.",
    "门后是梦层 {depth}。": "Beyond the door lies dream layer {depth}.",
    "裂隙只在初啼之渊。": "The rift exists only in the First Cry abyss.",
    "判断正确——这段记忆的确来自{origin}。（自我线索 +1）": "Correct — that memory truly comes from {origin}. (Self-clue +1)",
    "判断错了。它其实是{origin}。": "Wrong. It is actually {origin}.",
    "归档门沉默着——三间展室还没有被看完（{done}/3）。": "The archive door stays silent — the three exhibit rooms are not all seen ({done}/3).",
    "你把线索付之一炬。门开了。": "You burn the clues to ash. The door opens.",
    "牵引已接受。三个承担点在等你。": "The charge accepted. Three stations of burden await.",
    "承担 {count}/3。梦记下了这个承认。": "Burden {count}/3. The dream records this admission.",
    "审判门纹丝不动——承担 {count}/3，还差得远。": "The judgement door does not budge — burden {count}/3, far from enough.",
    "执笔者还在写着。笔没有空出来。": "The Scribe is still writing. No pen is free.",
    "自我线索不足（{have}/{need}）——这样的你还撑不起这个结局。": "Not enough self-clues ({have}/{need}) — you cannot carry this ending yet.",
    "想象力不足（{have}/{need}）——共写是要花力气的。": "Not enough imagination ({have}/{need}) — co-writing takes effort.",
    "故事到了最后一页……": "The story reaches its final page...",
    "这个选项什么也没发生。": "Nothing happens with this option.",
    "你选择了清晨。": "You choose the morning.",
    "—— 结局 · ": "— Ending · ",
    "初醒": "First Waking",
    "你醒了。": "You wake up.",
    "重写": "Rewrite",
    "放手": "Let Go",
    "共写": "Co-written",
    "沉没": "Sunk",
    "本局统计：": "Run stats: ",
    "梦层 {depth} · 回合 {rounds} · 击杀 {kills} · 自我线索 {clues}": "layer {depth} · rounds {rounds} · kills {kills} · self-clues {clues}",
    "按任意键返回主页": "Press any key to return to the home screen",
    "辅助瞄准：弹体命中失控意识。": "Assisted shot: the projectile hits an anomaly.",
    "辅助弹体击碎了一处坚实聚合物。": "The assisted shot shatters a solid aggregate.",
    "辅助弹体撞上坚实聚合物。": "The assisted shot slams into a solid aggregate.",
    "辅助弹体被坚实聚合物挡下。": "The assisted shot is blocked by a solid aggregate.",
    "辅助弹体飞出视野，消失在梦的深处。": "The assisted shot flies out of sight, vanishing into the dream.",
    "接取任务「{name}」。": "Quest accepted: {name}.",
    "任务兑现「{name}」。{detail}": "Quest completed: {name}. {detail}",
    "{name}送了你一件赠品。{detail}": "{name} gives you a gift. {detail}",
    "你向{name}交清了这一件。{detail}": "You settle this one with {name}. {detail}",
    "这项任务已经在任务簿里了。": "This quest is already in your ledger.",
    "先接取这个任务再来兑现。": "Take the quest before trying to redeem it.",
    "还没达成：{req}（{have}/{need}）。": "Not yet met: {req} ({have}/{need}).",
    "这一组赠品你已经领过了。": "You have already claimed from this gift set.",
    "要求：{req}": "Requires: {req}",
    "三选一赠品（限领一次）": "Pick-one gift (once only)",
    "解决失控意识 ×{n}": "Defeat {n} anomalies",
    "解决{target} ×{n}": "Defeat {target} ×{n}",
    "回应异常地点 ×{n}": "Respond to {n} anomaly sites",
    "到达第 {n} 层": "Reach layer {n}",
    "嘲讽把这一击引到了{watcher}身上！": "The taunt draws the strike onto {watcher}!",
    "房间折叠体挪到了别处。": "The folded room shifts itself elsewhere.",
    "远处传来倒放的鼓点——{n} 只异象循声而动。": "A reversed drumbeat sounds in the distance — {n} anomalies stir toward it.",
    "远处的纸页又翻动起来——纸页犬重新凝聚了。": "Pages rustle in the distance — the page hound re-forms.",
    "一声啼哭响彻整层梦——所有异象都听见了。": "A first cry rings through the whole layer — every anomaly hears it.",
    "你被推开了！": "You are shoved aside!",
    "水浸过全身，火焰熄了。": "Water soaks through and the flame dies.",
    "身上带着火苗：每回合心智 −1、清醒 −1，直到火焰熄灭（水或等待）。": "A flame clings to you: mind −1 and clarity −1 each round until it dies (water, or time).",
    "{name}被挤开了。": "{name} is squeezed aside.",
    "该格已有意识体，无法放置。": "That cell is occupied by a consciousness and cannot be placed on.",
    "燃烧": "Burning",
    "蓄电": "Piezo Charge",
    "{event}：命运递来{rarity}的{item}。": "{event}: fate hands you a {rarity} {item}.",
    "命运犹豫了一下——什么也没有发生。": "Fate hesitated — nothing happened.",
    "发射。": "Fired.",
    "打开了{item}。": "Opened the {item}.",
    "容器不在行囊里。": "The container is not in your inventory.",
    "（空的）": "(empty)",
    "本格液体：": "Liquid here: ",
    "本格气体：": "Gas here: ",
    "操作": "Actions",
    "盛装（从本格装入容器）": "Fill (from this cell into the container)",
    "倒出（倒在本格并就地反应）": "Pour (onto this cell, reacting in place)",
    "1 盛装 · 2 倒出 · Esc 收起": "1 fill · 2 pour · Esc close",
    "本格没有可盛装的液态记忆。": "No liquid memory here to fill with.",
    "本格没有可盛装的弥散印象。": "No diffuse impression here to fill with.",
    "{item}里已经装着{old}，先倒出再盛。": "The {item} already holds {old}; pour it out first.",
    "{item}已经装满了。": "The {item} is already full.",
    "盛装了 {kind} ×{n}（{left}/{cap}）。": "Filled {kind} ×{n} ({left}/{cap}).",
    "{item}是空的。": "The {item} is empty.",
    "倒出了 {kinds}。": "Poured out {kinds}.",
    "它咬走了一点想象力（−2）。": "It bites away a bit of imagination (-2).",
    "它让你忘掉了一种感觉：{portent} 被驱散。": "It makes you forget a feeling: {portent} dispelled.",
    "执笔者删去了你两笔想象力。": "The Scribe strikes out two points of your imagination.",
    "你败给了执笔者，故事被写进了它的稿纸。": "You lost to the Scribe; your story was written into its pages.",
    "你在深层边界沉没，梦收回了它的作者。": "You sank in the Deep Boundary, and the dream reclaimed its author.",
    "↑↓ 选参数 · -/= 调整 · l 放置 · Esc 取消": "↑↓ pick parameter · -/= adjust · l place · Esc cancel",
    "调试：已选择 {item}，按 l 在光标格释放。": "Debug: selected {item}; press l to release at the cursor cell.",
    "已选择：{item}（{cat}）· l 在光标格释放 · Esc 取消": "Selected: {item} ({cat}) · l releases at cursor · Esc cancels",
    "回应": "Respond",
    "铃兰薄荷的凉意直冲头顶：清醒度 +4。": "The mint's coolness rushes to your head: clarity +4.",
    "琥珀蕨的叶脉亮了起来：想象力 +4。": "The fern's veins light up: imagination +4.",
    "忘忧雏菊的白花瓣散着香气：心智 +3。": "The daisy's white petals breathe out scent: mind +3.",
    "彩玻菌的菌盖映出七彩：清醒度 +3。": "The mushroom cap throws rainbow light: clarity +3.",
    "低语蕨的秘密渗进耳中：心智 +4，清醒度 −1。": "The fern's secrets seep into your ear: mind +4, clarity −1.",
    "辅助瞄准中：按任一方向键发射。": "Assisted aiming: press any direction to fire.",
    "固定观察：": "Pinned: ",
    "目标 {t}：": "Target {t}: ",
    "左键相邻格行动；远处左键逐步寻路。右键交互列表，中键固定目标。Ctrl+左键加入快捷/固定。滚轮滚动记录。": "Left-click adjacent to act; far left-click walks a path. Right-click menu, middle-click pin. Ctrl+left-click shortcuts. Wheel scrolls the log.",
    "攻击": "Attack",
    "攻击（需确认）": "Attack (confirm)",
    "拾取": "Pick up",
    "回应": "Respond",
    "（已完成）": "(done)",
    "这项交易已经完成过了。": "This trade has already been made once.",
    "移动": "Move",
    "打开": "Open",
    "第 {a}-{b}/{c} 行 · 滚轮或 ↑↓ 滚动": "Lines {a}-{b}/{c} · wheel or ↑↓",
    "第 {a}-{b}/{c} 行 · 滚轮或 PgUp/PgDn 滚动": "Lines {a}-{b}/{c} · wheel or PgUp/PgDn",
    "第 {a}-{b}/{c} 条": "Rows {a}-{b}/{c}",
    "就地篡改（右栏简版）": "Tamper in place (panel lite)",
    "回到右栏继续改": "Back to the panel to keep editing",
    "也可以按 C 用地图侧篡改面板。": "Press C to use the map-side tamper panel instead.",
    "在地图里改：范围 / 落点 / 详情": "Edit on map: range / landing / details",
    "范围、聚流落点与效果详情在地图侧篡改面板。":
        "Range, gather landing and effect details are in the map-side tamper panel.",
    "这一句也能在右栏改：Esc 先回右栏简版。":
        "This line can also be edited in the panel: Esc returns to it first.",
    "程度：{value}（- = 切换）": "Degree: {value} (- = to switch)",
    "落点：{where}": "Landing: {where}",
    "观察格 ({x},{y})": "Observed cell ({x},{y})",
    "未选——用下面的入口转到地图侧": "Not chosen - use the entry below to switch to the map",
    "↑↓ 选词 · Enter 进确认 · Esc 退出": "↑↓ picks a word · Enter confirms · Esc exits",
    "↑↓ 选词 · ←→ 换目标 · Tab 切条件 · Space 勾选 · Enter 执行 · Esc 退出":
        "↑↓ picks a word · ←→ switches the target · Tab cycles conditions · Space toggles"
        " · Enter commits · Esc exits",
    "意识行囊": "Mind Inventory",
    "当前:": "Here:",
    "（空）": "(empty)",
    "（无）": "(none)",
    "行囊中的携带意象：": "Carried images in bag:",
    "冷却 {n} 回合": "Cooldown {n} rounds",
    "—— 主动构想 ——": "—— Active Conceptions ——",
    "尚未习得任何构想（书卷与残页中藏着它们）": "No conceptions learned yet (scrolls and pages hide them)",
    "操作界面": "Actions",
    "该意识属于稳定意识/受控意识，确认攻击？[Y/N]": "Stable/controlled consciousness — confirm attack? [Y/N]",
    "寻路中：剩余 {count} 格（点击或按键可中断）": "Pathing: {count} cells left (click or key to abort)",
    "未定形轮廓": "An unformed outline",
    "等待输入新的": "Press the new key for ",
    "；Q 或 Esc 取消。": "; Q or Esc to cancel.",
    "当前没有等待输入的按键。": "No key capture in progress.",
    "已取消按键捕获。": "Key capture cancelled.",
    "此分类暂无条目。": "No entries in this category.",
    "未知": "Unknown",
    "空白乐谱": "Blank Score",
    "编辑留下的批注": "Editor's Annotation",
    "无人检票的站台": "Unticketed Platform",
    "玻璃里的第二个房间": "Second Room in the Glass",
    "发潮的卧室": "Damp Bedroom",
    "重叠的阳台": "Overlapping Balconies",
    "倒悬的图书馆": "Inverted Library",
    "无声的剧场": "Silent Theatre",
    "幻觉空间·凝胶回廊": "Hallucination·Gel Corridors",
    "幻觉空间·熔化的钟表店": "Hallucination·Molten Clockworks",
    "幻觉空间·倒放的花园": "Hallucination·Rewound Garden",
    "幻觉空间·悬浮的楼梯井": "Hallucination·Floating Stairwells",
    "幻觉空间·吞声的湖底": "Hallucination·Soundless Lakebed",
    "幻觉空间·蜡质的剧场": "Hallucination·Waxen Theatre",
    "幻觉空间·错位的电梯": "Hallucination·Misaligned Elevator",
    "幻觉空间·无限镜像": "Hallucination·Endless Mirrors",
    "幻觉空间·崩解的边界": "Hallucination·Dissolving Rim",
    "幻觉空间·梦的核心": "Hallucination·Core of the Dream",
    "第二十梦层——梦的核心——没有更深的入口。": "Layer 20 — the Core of the Dream — has no deeper entrance.",
    "未知的构想。": "Unknown conception.",
    "你还没有习得这个构想。": "You have not learned this conception.",
    "想象力不足（需要 {cost}）。": "Not enough imagination (needs {cost}).",
    "清醒度不足（需要 {cost}）。": "Not enough clarity (needs {cost}).",
    "、": ", ",
    "；": "; ",
    "＋": " + ",
    "资源不足（需要 {cost}）。": "Not enough resources (needs {cost}).",
    # ---- 环境条件场景（重构方案 §10／§12.1，R01 借火的小术阵／R02 引潮的低盆）----
    # 条件说明、拒绝原因与面板行都来自 world/scenes.py 的同一份条件结构，
    # 所以这里的键必须与解释器里的模板逐字一致（§10.1「不允许文案说一套、逻辑做一套」）。
    "这台设施已经不在这儿了。": "That fixture is no longer here.",
    "先不碰它": "Leave it alone for now",
    "尚未辨认的条件。": "A condition you have not made out yet.",
    "这条条件暂时无法确认（类型 {kind} 未知）。": "This condition cannot be confirmed for now (unknown type {kind}).",
    "{name}：{state}": "{name}: {state}",
    "{name}还没被看清——走近到能看见它的位置，才知道现在能不能动。":
        "The {name} has not been made out yet — come close enough to see where it stands before asking what it can do.",
    "你在{name}旁边。": "You are beside the {name}.",
    "离{name}太远（要 {radius} 格以内，现在 {near} 格）。":
        "Too far from the {name} (within {radius} cells, now {near}).",
    "{name}不在这里。": "There is no {name} here.",
    "{name}的火势 {flame}。": "The {name} burns at {flame}.",
    "{name}还没有火。": "The {name} has no fire yet.",
    "{name}已经烧着了。": "The {name} is already burning.",
    "{name}还接得住火。": "The {name} can still catch fire.",
    "{name}已经烧穿，点不着了。": "The {name} has burned through — nothing will catch here.",
    "边槽还有 {have} 处燃料。": "{have} side slots still hold fuel.",
    "边槽里的燃料不够（要 {need} 处，只剩 {have} 处）。":
        "Not enough fuel in the side slots (need {need}, only {have} left).",
    "术阵地面可接火 {have} 格。": "The ward floor can take fire on {have} cells.",
    "术阵地面还接得住火（{have} 格），不用重新装料。":
        "The ward floor still takes fire ({have} cells) — no need to reload.",
    "术阵地面已经烧成灰——先装料。": "The ward floor has burned to ash — reload it first.",
    "作用区里没有火。": "No fire in the area.",
    "作用区里还有 {have} 格在烧。": "{have} cells in the area are still burning.",
    "{name}：{have}。": "{name}: {have}.",
    "{name}不够（要 {need}，只有 {have}）。": "Not enough {name} (need {need}, only {have}).",
    "{name}不足（要 {need}，只有 {have}）。": "Not enough {name} (need {need}, only {have}).",
    "{name}已经满了。": "The {name} is already full.",
    "不在冷却里。": "Not cooling down.",
    "还在冷却——要等到第 {until} 世界回合（现在 {now}）。":
        "Still cooling down — wait until world round {until} (now {now}).",
    "设施：{state}。": "Fixture: {state}.",
    "设施现在是「{state}」，这一步要等它回到：{want}。":
        "The fixture is {state}; this step needs it back in: {want}.",
    "{name}有 {kind} {amount} 单位。": "The {name} holds {amount} units of {kind}.",
    "{name}里不是允许的液体（现在是{found}）。":
        "The {name} does not hold an allowed liquid (now {found}).",
    "{name}只有 {amount} 单位，要到 {need}。": "The {name} holds only {amount} units; it needs {need}.",
    "排放区通着。": "The discharge area is clear.",
    "排放区有 {n} 格堵着。": "{n} cells of the discharge area are blocked.",
    "排放区里挡着 {name}。": "{name} is blocking the discharge area.",
    "排放区里没有能搬动的东西。": "Nothing in the discharge area can be moved.",
    "作用区是安全的。": "The area is safe.",
    "作用区里还有 {n} 格危险。": "{n} cells in the area are still hazardous.",
    "带着 {name} ×{have}。": "Carrying {name} ×{have}.",
    "这台设施不会做这个。": "This fixture cannot do that.",
    "这台设施的定义已经找不到了。": "This fixture's definition can no longer be found.",
    "那处设施不在这一层。": "That fixture is not on this layer.",
    "这道命令的效果不在允许清单里（{kind}）。": "This command's effect is not on the allowed list ({kind}).",
    "这一步要改的格子太多，先停下来（上限 {limit}）。":
        "This step would change too many cells — stopping (limit {limit}).",
    "冷却到第 {until} 世界回合（现在第 {now} 回合）。":
        "Cooling down until world round {until} (now round {now}).",
    "储量：{stock}": "Stock: {stock}",
    "· {label}——现在就能做。{cost}": "· {label} — ready to do now.{cost}",
    "· {label}——{why}": "· {label} — {why}",
    "（代价：{cost}）": " (cost: {cost})",
    "这里的地面接不住火——什么也不会发生。": "This floor won't take fire — nothing would happen.",
    "术阵地面接不住火——先装料。": "The ward floor won't take fire — reload it first.",
    "没有能落脚的格子，水过不去。": "There is no cell for the water to reach.",
    "盆里已经没有水了。": "The basin has no water left.",
    "管道余量已经空了。": "The pipe reserve is empty.",
    "搬不动——周围没有能放的地方。": "Can't move it — nowhere nearby to set it down.",
    "{name}烧起来了。": "The {name} catches fire.",
    "术阵开始预热：下一个行动后成火场。":
        "The ward begins to prime: the fire field lands after your next action.",
    "术阵的火场起来了（{n} 格）。": "The ward's fire field takes hold ({n} cells lit).",
    "{name}的火被踩灭了。": "You stamp out the fire in the {name}.",
    "干纸重新铺满术阵（{n} 格）。": "Dry paper is relaid across the ward ({n} cells).",
    "放出了 {kind} ×{n}。": "Released {kind} ×{n}.",
    "把 {name} 搬到了外面。": "You carried the {name} out of the way.",
    "{name} +{n}。": "{name} +{n}.",
    "收进行囊：{name} ×{n}。": "Stowed: {name} ×{n}.",
    "{name}的火场过去了，这条路重新打通。": "The {name}'s fire field has passed; this way is open again.",
    # 生命周期状态与锚点／储量名是查表取的动态字符串，coverage 测试抓不到，
    # 但面板与拒绝原因都会把它们插进句子里，所以同样要有英文。
    "休眠": "Dormant",
    "可激活": "Ready",
    "预告": "Primed",
    "耗尽": "Spent",
    "术阵燃料": "Ward fuel",
    "备用干纸": "Spare paper",
    "管道余量": "Pipe reserve",
    "火盆": "brazier",
    "边槽": "side slots",
    "术阵": "ward",
    "旁路": "bypass",
    "蓄水盆": "basin",
    "上游阀": "upstream valve",
    "低槽": "low channels",
    "排放区": "discharge area",
    "空的": "nothing",
    "这里": "here",
    "／": " / ",
    "控制台": "console",
    "内院喇叭": "yard horn",
    "门口喇叭": "gate horn",
    "余电": "Residual charge",
    "{name}方向有 {have} 个听得见的失控意识。":
        "{have} runaway awareness(es) can hear this direction from the {name}.",
    "{name}方向没有听得见的失控意识（要 {need} 个，现在 {have} 个）。":
        "Nothing can hear the {name} in this direction (need {need}, now {have}).",
    "这个方向没有听得见的失控意识——喊了也没人跟着走。":
        "No one hears this direction — shouting would move nobody.",
    "喇叭把呼叫送向{name}。": "The call goes out through the {name}.",
    "会喊话的静电台": "The Console That Talks Back",
    "两只喇叭口一只朝着内院、一只朝着门口，旋钮边上还剩几格电，台面连着一条能走的路。":
        "Two horns, one facing the yard and one the gate; a few bars of charge left by the dial, "
        "and a walkable line up to the face of the console.",
    "机壳内侧刻着一行：喊给谁听，先选方向。": "Scratched inside the case: decide who hears it — first pick a direction.",
    "把呼叫打向内院喇叭": "Send the call to the yard horn",
    "以固定半径 5 发出一次声源：这个方向听得见的失控意识会把它当作此刻知道的位置。":
        "One sound source at a fixed radius of 5: anything in this direction that hears it "
        "takes it as the position it currently knows.",
    "把呼叫打向门口喇叭": "Send the call to the gate horn",
    "换一只喇叭口：同一次呼叫只可能有一个落点，两个方向因此互斥。":
        "Swap horns: a single call can only land in one place, so the two directions exclude each other.",
    "取出台里的备用电池芯": "Take the spare cell out of the console",
    "拆开就少一次呼叫——换一枚能装进别处的电池背面。":
        "Open it up and lose a call — for one battery back that fits somewhere else.",
    "把电池背面装回台面": "Fit a battery back into the console",
    "一枚电池芯够喊一次。": "One cell is enough for a single call.",
    # 场景定义里的名称／描述／线索／命令标签与说明是数据字段，不经过 tr("字面量")
    # 扫描，所以逐条补在这里；面板读的就是这些键（§14）。
    "借火的小术阵": "A Small Ward Lit by Borrowed Flame",
    "浅槽围着填了干纸的火盆，两处边槽还压着燃料；外侧一条不燃的地面绕开整座院子。":
        "Shallow grooves ring a brazier stuffed with dry paper; two side slots still hold fuel. "
        "Outside, a strip of floor that will not burn loops around the whole yard.",
    "槽边刻着一行：先有火，再谈阵。": "Carved along the groove: first a fire, then a ward.",
    "借火：把火盆点亮": "Borrow flame — light the brazier",
    "花一点想象力引槽里的干纸。旁边已有火源时火会自己爬过来，不必花这一笔。":
        "Spend a little imagination on the paper in the groove. Where a fire already neighbours it, "
        "the flame creeps over by itself — no need to pay then.",
    "启动术阵（预警一个行动后成火场）": "Start the ward (a fire field is warned one action ahead)",
    "作用区在下一个实际行动后一起烧起来：干纸的燃料够撑 4 回合，之后余火还会自己拖几回合才熄；烧完的地面不会自己长回来。":
        "The area catches together after your next real action: dry paper carries four rounds of fuel, "
        "then the embers drag a few more rounds before they die. Burned floor does not grow back on its own.",
    "把燃料仓的干纸重新铺进术阵": "Relay the ward with paper from the fuel store",
    "地面烧成灰之后，只有装料才能再画一次。": "Once the floor is ash, only reloading lets you draw it again.",
    "取走燃料仓里的干纸": "Take the dry paper out of the fuel store",
    "带走就失去第二次用量——换两件能塞进别处的东西。":
        "Take it and lose the second charge — for two things that fit somewhere else.",
    "把行囊里的残页塞进燃料仓": "Feed a torn page from your pack into the fuel store",
    "一张残页够画一次。": "One torn page is enough for a single drawing.",
    "踩熄火盆里的火": "Stamp out the brazier",
    "想让这条线安静下来时，随时可以。": "Any time you want this line to go quiet.",
    "引潮的低盆": "The Low Basin That Draws the Tide",
    "一只浅盆接着两条低槽，槽口通向一片排放区；上游阀门还剩多少看得见。":
        "A shallow basin feeds two low channels whose mouths open onto a discharge area; "
        "how much the upstream valve still holds is written where you can read it.",
    "阀体上刻着余量：放水之前先数一数盆里有多少。":
        "Scratched on the valve body: count what the basin holds before you let it out.",
    "打开上游阀（3 单位进盆）": "Open the upstream valve (3 units into the basin)",
    "管道里只剩这些：开一次给 3 单位，开关冷却 2 世界回合。":
        "That is all the pipe has left: one opening gives 3 units, then the valve cools for 2 world rounds.",
    "把排放区里的挡路物搬到外面": "Carry whatever blocks the discharge area out",
    "可移动的杂物搬开，水路才算通——它还在地图上，只是不堵着了。":
        "Only with the movable clutter cleared is the waterway open — it stays on the map, just no longer in the way.",
    "开闸：把盆里的水放进排放区": "Open the gate — let the basin's water into the discharge area",
    "至多 6 单位，按盆里实有的量给；水面按既有规则自己铺开。":
        "At most 6 units, limited by what the basin actually holds; the surface spreads by the water rules already in place.",
    # --- S03 配对折页点（§9 R04 两端折页渡口）：布局键、储量与命令/结算文案
    "内侧折页": "the inner fold",
    "外侧折页": "the outer fold",
    "两张折页": "either fold",
    "内侧折页四周": "around the inner fold",
    "外侧折页四周": "around the outer fold",
    "对折次数": "Foldings left",
    "对折的渡口": "The Ferry That Folds in Two",
    "两张空白折页隔着一段路面对面立着，各自四周都是走得进的地面；两边都折稳之后，它们之间就成了一条固定的对折线。":
        "Two blank folds stand facing each other across a stretch of walking ground; once both are creased firm, a fixed fold-line runs between them.",
    "页脚印着一行：两边都立住了，才谈对折。":
        "Printed in the footer: both sides must stand before anything can fold.",
    "把内侧折页折稳": "Crease the inner fold firm",
    "折稳的那一格会反出光来，对折线这才少了一头的悬空。":
        "The creased cell starts throwing back light — now the fold-line has one less end left hanging.",
    "把外侧折页折稳": "Crease the outer fold firm",
    "另一头要在另一头站上去折——两边不能隔着路一起立住。":
        "The far end is creased by standing on it — you cannot set both sides firm across the road.",
    "对折到另一张折页那侧": "Fold across to the other page",
    "只在这对端点之间折：落点取对端最近的合法空格，找不到就不付这一笔。敌人照样走完它们的那一拍。":
        "Only ever between this pair of ends: you land on the nearest legal cell at the far end, and if there is none you pay nothing. The others still take their turn.",
    "{name}已经折稳了，不用再折。": "The {name} is already creased firm — no need again.",
    "{name}还没折稳——站上去才折得了。":
        "The {name} is not creased yet — you have to stand on it to firm it up.",
    "{name}已经折稳。": "The {name} is creased firm.",
    "{name}还没折稳。": "The {name} is not creased yet.",
    "这对折页已经不在这一层了。": "This pair of folds is no longer on this layer.",
    "你得站在某一张折页上才折得过去。": "You have to be standing on one of the folds to fold across.",
    "另一侧没有能落脚的格子——不把你折进墙里。":
        "There is nowhere to land on the far side — the fold will not put you into a wall.",
    "{name}被折稳了。": "The {name} is creased firm now.",
    "你被折到了{name}那一侧。": "The fold puts you down beside {name}.",
    # --- S10 泵房保护区（§7.2「泵房的狩猎登记」两解）：布局键、条件／结算文案
    "保护区": "protected yard",
    "侧门": "side door",
    "门柱手柄": "winch on the door post",
    "泵机": "pump",
    "{name}里还站着 {have} 个失控意识。":
        "The {name} still has {have} runaway awareness(es) standing in it.",
    "{name}里没有站着的东西（要 {need} 个，现在 {have} 个）。":
        "Nothing stands in the {name} (need {need}, now {have}).",
    "{name}里站着 {have} 个失控意识。":
        "{have} runaway awareness(es) are standing in the {name}.",
    "{name}是空的。": "The {name} is empty.",
    "{name}的挡板已经落下了，不用再放。":
        "The {name}'s board is already down — no need to drop it again.",
    "{name}还开着。": "The {name} is still open.",
    "{name}的挡板落着。": "The {name}'s board is down.",
    "这道门不在这一层了。": "This doorway is no longer on this layer.",
    "挡板已经落下了。": "The board is already down.",
    "挡板上正站着东西——落下去会把它压进地里。":
        "Something is standing on the board — dropping it would press that thing into the ground.",
    "{name}的挡板落下了。": "The {name}'s board drops into its slot.",
    "{name}连着 {n} 个世界回合没有失控意识踩进去——这一条记在你账上。":
        "No runaway awareness has set foot in the {name} for {n} straight world rounds — "
        "that goes on your record.",
    # --- §7.1／§7.3 任务实例：接活绑实例、三条归属与一次性销账
    "{message}（{why}）": "{message} ({why})",
    "这项任务的解法这里还认不出来。": "This desk cannot yet recognise how that task is resolved.",
    "这一层没有出过事的{name}——登记员不给空单。":
        "There is no incident-marked {name} on this layer — the registrar will not write a blank order.",
    "那一位已经不在了，但不是你办的——只认一次确认现场。":
        "That one is already gone, but not by your hand — only a single scene confirmation counts.",
    "已成立：{kind}": "Established: {kind}",
    "两条都还差：当场解决那一位，或把它引出院子、放下侧门挡板，让{name}连着 {n} 个世界回合没有失控意识踩进去。":
        "Both ways are still open: deal with that one on the spot, or lure it out of the yard and "
        "drop the side-door board so that no runaway awareness sets foot in the {name} for {n} "
        "straight world rounds.",
    "这一单已经销过账了——回旧层也再领不出第二份。":
        "That order has already been settled — going back to an old layer will not pay it out twice.",
    "还没达成：{why}": "Not yet met: {why}",
    "要拿到{name}的使用权，得回到它那一层的门口——这一层办不了。":
        "To take the {name} into your use you must be back at its own layer's doorway — "
        "this layer cannot sign for it.",
    "{name}的挡板被抬回去了——这院子现在归你用。":
        "The {name}'s board has been lifted back out — this yard is yours to use now.",
    "击败": "Defeated",
    "诱离封守": "Lured out and held",
    "确认现场": "Scene confirmed",
    # 场景与任务定义里的名称／描述／线索／命令与报酬文案同样是数据字段（§14）。
    "泵房的保护区": "The Pump Room's Protected Yard",
    "泵机在走道那一头空转，保护区就是走道边的一块空地，侧门是它朝着走道的那一面，挡板的手柄钉在门外的墙柱上；协会把这里当临时存放点，如今里头窝了一位不请自来的。":
        "A pump idles at the far end of the walkway, and the protected yard is the patch of open "
        "floor beside it, its side door facing the walkway; the board's winch is nailed to the "
        "wall post outside the door. The association keeps this as a temporary store — a squatter "
        "has since moved in uninvited.",
    "门框上钉着登记条：那位解决之前，泵房不开张。":
        "A registry slip is nailed to the doorframe: until that one is accounted for, "
        "the pump room stays shut.",
    "让泵机空转一声": "Let the pump grind once",
    "喊声落在走道那一头空转的泵机上：那位要过来看，就得先离开庭院那几格。":
        "The noise lands on the pump idling at the far end of the walkway: for that one to come "
        "and look, it has to leave the yard's own cells first.",
    "在门柱手柄边放下侧门挡板": "Drop the side-door board by the winch on the door post",
    "挡板落下就卡死在门槽里，要抬起来得回协会领工单——手柄在门外的墙柱上，它封的是回院子最近的那一步；挡板上正站着东西时不放。":
        "Once down, the board jams in its slot, and lifting it again takes a work order from the "
        "association — the winch sits on the wall post outside the door, and what it closes is the "
        "nearest step back into the yard; it will not fall while something stands on the board.",
    "泵房的狩猎登记": "Hunting Registry for the Pump Room",
    "解决泵房里那一位：当场击败，或引出院子、放下侧门挡板，让保护区连着 3 个世界回合没有失控意识踩进去":
        "Settle the one in the pump room: defeat it on the spot, or lure it out of the yard and "
        "drop the side-door board so that no runaway awareness sets foot in the protected yard "
        "for 3 straight world rounds",
    "泵房使用权＋一份物资": "Use of the pump yard plus a supply",
    "一次协会回收服务": "One association collection service",
    "泵房里窝了一位。要么当场解决它，要么让泵机空转一声把它引出院子、在门柱手柄边放下侧门挡板，连着三个世界回合别让失控意识踩进保护区——回来销账时说要哪一档报酬。":
        "Some one has taken up in the pump room. Either deal with it there and then, or let the "
        "pump grind once to draw it out, drop the side-door board by the winch on the door post, "
        "and keep no runaway awareness from setting foot in the protected yard for three straight "
        "world rounds — and say which tier of payment you want when you come back to settle.",
    "「泵房那间保护区里窝了一位。当场解决也好，引出来把侧门挡板放下、连着三个回合别让它踩进去也好——两条都算数，但得先接登记单。」":
        "\"There's a squatter in the pump room's protected yard. Sort it out on the spot, or lure "
        "it out and drop the side-door board and keep it from stepping back in for three rounds — "
        "either counts, but you take the registry order first.\"",
    "接取任务：泵房的狩猎登记": "Take the task: Hunting Registry for the Pump Room",
    "销账：泵房那位有了归属（要泵房使用权＋一份物资）":
        "Settle: the pump room one has an owner now (for use of the yard plus a supply)",
    "销账：泵房那位有了归属（要一次回收服务）":
        "Settle: the pump room one has an owner now (for one collection service)",
    # --- S01 候车与旁路（§8）：布局键、具名开关、条件／结算文案与场景定义字段
    "路线牌": "route board",
    "候车厅": "waiting hall",
    "窗边窄路": "narrow window walk",
    "候车票": "Waiting ticket",
    "标出的旁路": "marked bypass",
    "中继权限": "relay access",
    "旅人服务": "traveller service",
    "{name}上还挡着 {item}。": "{item} is still in the way on the {name}.",
    "{name}上没有能搬动的东西。": "Nothing movable is in the way on the {name}.",
    "{name}上挡着 {item}。": "{item} is in the way on the {name}.",
    "{name}上通着。": "The {name} is clear.",
    "{name}已经立住了，不用再来一次。": "The {name} is already set firm — no need for a second time.",
    "{name}还没着落——先把前一步做完。": "The {name} is not settled yet — finish the earlier step first.",
    "{name}已经立住。": "The {name} stands firm.",
    "{name}还没立住。": "The {name} is not standing yet.",
    "这条路已经标出来了——没有新的一格会亮起来。":
        "This route is already marked — no new cell would light up.",
    "地上亮起一条路（{n} 格）。": "A route lights up on the floor ({n} cells).",
    "换乘站的候车厅": "The Transfer Station's Waiting Hall",
    "路线牌立在大厅这一头，牌上三条线都绕回同一个大厅；一条贴着窗的窄路被杂物堵着，另一侧还剩一条没人走的旁路。牌座下压着一张没有盖章的候车票。":
        "The route board stands at this end of the hall, its three lines all winding back to the "
        "same hall; a narrow walk along the window is clogged with clutter, and on the other side "
        "one unwalked bypass remains. A waiting ticket, unstamped, is pressed under the board's base.",
    "牌座刻着一行：先把旁路认下来，再看窗边那条通不通。":
        "Carved on the board's base: reckon the bypass first, then see whether the window walk is clear.",
    "读路线牌，把旁路标在地上": "Read the route board and mark the bypass on the floor",
    "认下这条没人走的旁路：标出来的那几格会反出光来。牌上也顺带指出窗边那条窄路被什么堵着。":
        "Reckon this unwalked bypass: the cells you mark throw back light. The board also points out "
        "what is clogging the narrow window walk.",
    "把堵在窗边窄路上的杂物挪开": "Clear the clutter out of the narrow window walk",
    "搬开之后窗边这条路才通——它还在地图上，只是不堵着了。":
        "Only once carried away is the window walk open — it stays on the map, just no longer in the way.",
    "把票交给站台，换一次中继权限": "Hand the ticket to the platform for one relay access",
    "中继权限要把窗边那条路先打通：路还堵着，票换不来任何东西。":
        "Relay access needs the window walk cleared first: while it is clogged, the ticket buys nothing.",
    "取走候车票": "Take the waiting ticket",
    "带走就换不到中继权限，也留不下旅人补给——票只有这一张。":
        "Take it and you can buy no relay access nor leave the traveller service — there is only this one ticket.",
    "把票留在站台，换一份旅人补给": "Leave the ticket at the platform for a traveller's supply",
    "把票留在原处，旅人服务就照旧开着——换一份能带走的热饮。":
        "Leave the ticket where it lies and the traveller service stays open — take a hot drink you can carry.",
    # --- S09 档案辨认（§8）：布局键、具名开关、场景定义字段与命令文案
    "编目台": "catalog desk",
    "档案架": "the stacks",
    "编目索引": "catalog index",
    "安全路线": "safe route",
    "认出的记录": "identified record",
    "拆下的记录": "extracted record",
    "留档的记录": "filed record",
    "标出的安全路线": "marked safe route",
    "档案馆的编目台": "The Archive's Catalog Desk",
    "编目台立在档案架这一头，架上的记录按回声而不是按年份排列；索引卡还空着，"
    "另一侧一条通向外面的窄路从没有人标过。":
        "The catalog desk stands at this end of the stacks, whose records are ordered by echo "
        "rather than by year; the index cards are still blank, and on the other side a narrow "
        "walk out has never been marked by anyone.",
    "台面刻着一行：先认出是哪一页，再决定留、拆、还是交。":
        "Carved on the desk: first make out which page it is, then decide to keep, pull, or hand it in.",
    "照编目核对，认出那页具名记录": "Check the catalog and make out the named record",
    "把那页从回声里挑出来：索引卡会被点亮。认出来之前，留、拆、交都无从谈起。":
        "Pick that page out of the echo: the index cards light up. Until it is made out, keeping, "
        "pulling, and handing in are all moot.",
    "把记录留回架上，保留当地服务": "Leave the record in the stacks and keep the local service",
    "留在这里，档案馆的台面就照旧开着——换一次能带走的当地服务。":
        "Left here, the archive's desk stays open — take one local service you can carry away.",
    "把那页记录拆出来带走": "Pull the record out and take it away",
    "拆走就没有服务，也标不出安全路线——要换别的，先把这一页交回去。":
        "Pull it and there is no service, nor any safe route marked — to trade for either, hand the page back first.",
    "把拆下的记录交给档案员，换一条安全路线": "Hand the pulled record to the archivist for a safe route",
    "带着那页交到台面上：外侧那条没人标过的窄路会被标成一条安全路线。":
        "Bring that page to the desk: the unmarked narrow walk outside is marked as a safe route.",
    # --- 任务实例协议扩容（§7.1 模板 3/5：回收递送＋调查辨认，2026-10-11）---
    "完成交付": "Delivery made",
    "调查成立": "Investigation closed",
    "还差：{req}（{have}/{need}）——备好了当面点收。":
        "Still needed: {req} ({have}/{need}) — bring it over and we'll count it in person.",
    "还差：在{name}把线索一条条查清（{have}/{need}）。":
        "Still needed: chase down the clues at {name} one by one ({have}/{need}).",
    "还差：{req}。": "Still needed: {req}.",
    "交付{item} ×{n}": "Delivered {item} ×{n}",
    "你把这一条记在了心里。": "You make a note of it.",
    "这一条你已经在册子上记过了。": "You've already written this one down.",
    # 头版显影（§7.2）
    "头版的油墨": "The Front-Page Ink",
    "把 3 单位显影液倒进报童的印版托盘（他站着的那格）":
        "Pour 3 units of developer fluid into the paper boy's printing tray (the tile he stands on)",
    "一张头版＋一份补给": "A front page plus one supply",
    "一次排版帮工": "One typesetting favor",
    "报童要印一份「醒着的报纸」：把 3 单位显影液倒进他站的托盘格，他要拿去调油墨。":
        "The paper boy wants to print a 'waking paper': pour 3 units of developer fluid into the "
        "tray he stands on — he needs it to mix his ink.",
    "交货：显影液 ×3（要一张头版＋一份补给）": "Deliver developer fluid ×3 (for a front page plus one supply)",
    "交货：显影液 ×3（要一次排版帮工）": "Deliver developer fluid ×3 (for one typesetting favor)",
    # 监视者的三页（§7.2）
    "监视者的页码": "The Watcher's Pages",
    "找回 3 页协会账页（档案馆编目台拆页，或从纸页犬身上取回）":
        "Recover 3 registry pages (pull them at archive catalog desks, or take one off a page hound)",
    "一份线轴补给": "A spool-and-supply bundle",
    "一次协会护理": "One association checkup",
    "纸页犬咬走了协会的账本页。散页有实际去向：3–17 层的档案馆编目台能拆出一页，"
    "纸页犬身上也带着一页——凑够 3 页回来销账。":
        "Page hounds made off with the association's ledger pages. The loose pages have real "
        "whereabouts: archive catalog desks on floors 3–17 each give one up, and a page hound "
        "carries one too — gather 3 and come settle the account.",
    "销账：3 页协会账页（要一份线轴补给）": "Settle: 3 registry pages (for a spool-and-supply bundle)",
    "销账：3 页协会账页（要一次协会护理）": "Settle: 3 registry pages (for one association checkup)",
    # 遗失物有名字（§7.2）
    "遗失物有名字": "The Lost Thing Has a Name",
    "在候车厅查两处证据（失物登记册＋行李签），确定那只玻璃瓶的物主":
        "Check two clues in the waiting hall (the lost-property register and the luggage tag) "
        "to identify the glass bottle's owner",
    "交还失主，换一次招领服务": "Return it to the owner for one lost-and-found service",
    "代为保管，换一条旁路情报": "Keep it safe for a tip about a bypass",
    "声明占有（招领处会记住这瓶归了你）": "Claim it as yours (the lost-and-found will remember)",
    "候车厅里压着一件没人认领的失物。查失物登记册、再对窗边杂物上的行李签，"
    "两处证据对上就定了物主——归还、代管还是声明占有，销账时说清楚。":
        "An unclaimed lost thing sits in the waiting hall. Check the lost-property register, "
        "then match the luggage tag on the clutter by the window — once the two clues line up "
        "the owner is settled. Return it, keep it, or claim it; say so when you settle.",
    "接取任务：遗失物有名字": "Take the task: The Lost Thing Has a Name",
    "销账：物主查明了——交还失主，换一次招领服务": "Settle: owner identified — return it for one lost-and-found service",
    "销账：物主查明了——代为保管，换一条旁路情报": "Settle: owner identified — keep it safe for a bypass tip",
    "销账：物主查明了——声明占有那只瓶": "Settle: owner identified — claim the bottle as yours",
    # 一杯给醒着的人（§7.2）
    "一杯给醒着的人": "A Drink for the Waking",
    "把候车厅的长椅铺成旅人的铺位，让大厅连着 3 个世界回合没有火、没有失控意识踩进去":
        "Lay the hall bench into a traveler's bedroll, then keep the hall free of fire and "
        "strays for 3 world rounds in a row",
    "避难点开放＋一份温饮": "The shelter opens plus one warm drink",
    "一次夜班照料": "One night-shift care",
    "候车厅是旅人歇脚的地方，只是还没人收拾：把长椅铺成铺位，守着大厅连着三个"
    "世界回合别让失控意识踩进去——回来换一杯给醒着的人的茶。":
        "The waiting hall is where travelers rest, only nobody has tidied it: lay the bench "
        "into a bedroll and keep the hall free of strays for three world rounds in a row — "
        "come back for a drink for the waking.",
    "兑现：避难点收拾好了（要避难点开放＋一份温饮）": "Turn in: the shelter is ready (for an open shelter plus one warm drink)",
    "兑现：避难点收拾好了（要一次夜班照料）": "Turn in: the shelter is ready (for one night-shift care)",
    # 诗的下半句（§7.2）
    "诗的下半句": "The Other Half of the Poem",
    "在对折的渡口把内外两张折页都折稳，听全两处回声":
        "Steady both the inner and outer folded pages at the fold ferry and hear both echoes in full",
    "一份晨露＋他替你记下的一句": "Morning dew plus a line he writes down for you",
    "一次润笔": "One polishing of the quill",
    "诗人丢了下半句诗。对折的渡口那两张空白折页本身就是诗页：把内外两端都折稳，"
    "回声会漏出他要的词——回来念给他听。":
        "The poet lost the other half of his poem. The two blank folded pages at the fold ferry "
        "are poem pages themselves: steady both ends and the echo will leak the words he wants — "
        "come back and recite them.",
    "念出回声里的下半句（要一份晨露＋他替你记下的一句）": "Recite the echoed half-line (for morning dew plus a written line)",
    "念出回声里的下半句（要一次润笔）": "Recite the echoed half-line (for one polishing of the quill)",
    # 候车厅新增命令（§7.2 遗失物有名字／一杯给醒着的人）
    "把长椅铺成旅人的铺位": "Lay the bench into a traveler's bedroll",
    "铺好的那一格会反出光来。铺位立住之后，候车厅才开始给旅人记「连着安全」的账。":
        "The made-up tile will catch the light. Only once the bedroll stands does the hall "
        "start keeping a 'held safe' tally for travelers.",
    "查候车厅的失物登记册": "Check the waiting hall's lost-property register",
    "册子上一行墨迹未干：「一只带软木塞的玻璃瓶，失主候车时落下的。」":
        "A fresh line of ink in the register: 'One corked glass bottle, left behind by a "
        "traveler while waiting.'",
    "对窗边杂物上的行李签": "Match the luggage tag on the clutter by the window",
    "签上的名字与册子那行对上了：瓶子是候车厅旅人的——归还、代管还是声明占有，你来定。":
        "The name on the tag matches the register: the bottle belongs to a traveler of the "
        "hall — return it, keep it, or claim it; your call.",
    # 对折渡口（§7.2 诗的下半句）：折稳时漏出的回声
    "折稳的那一格会反出光来，对折线这才少了一头的悬空。纸页贴着耳朵时有极轻的回声。":
        "The steadied tile catches the light, and the fold line loses one hanging end. Held to "
        "your ear, the page carries a faint echo.",
    "另一头要在另一头站上去折——两边不能隔着路一起立住。这一张的回声比内侧那张低半个音。":
        "The far end has to be steadied from the far side — the two can't stand while you stand "
        "between them. This page's echo sits half a tone lower than the inner one.",
}

# 去掉占位键（值为 None 的键不参与翻译，避免误登记）。
EN = {key: value for key, value in EN.items() if value is not None}

# 内容与界面补充分册（见 i18n_content_en / i18n_ui_en）：新内容随写随加，
# 不必挤进本文件；冲突时以这里（上面）的既有条目为准。
from .i18n_content_en import EN_CONTENT, EN_UNCONSCIOUS, EN_EVENTS_SEP18, EN_MATERIALS_SEP18, EN_MATERIALS_PACK_V1, EN_ITEMS_PACK_V1, EN_EVENTS_DIALOGUE_LABELS, EN_PORTENT_REBALANCE_LABELS, EN_BUILD_BRIDGE  # noqa: E402
from .i18n_ui_en import EN_MESSAGES, EN_PLACES, EN_RUN_OPTIONS, EN_UI  # noqa: E402
from .i18n_equipment_en import EN_EQUIPMENT

EN = {**EN_CONTENT, **EN_UNCONSCIOUS, **EN_EVENTS_SEP18, **EN_MATERIALS_SEP18, **EN_MATERIALS_PACK_V1, **EN_ITEMS_PACK_V1, **EN_EVENTS_DIALOGUE_LABELS, **EN_PORTENT_REBALANCE_LABELS, **EN_BUILD_BRIDGE, **EN_PLACES, **EN_MESSAGES, **EN_UI, **EN_RUN_OPTIONS, **EN, **EN_EQUIPMENT}

# 意识状态分档标签（0-3 档：健康/受损/危险/紧急）。
STATUS_TIERS: tuple[str, str, str, str] = ("健康", "受损", "危险", "紧急")

EN.update(EN_UNCONSCIOUS)

EN.update({
    # ---- 拾取文本：携带意象 ----
    "拾取携带意象：{item}。": "Picked up a carried image: {item}.",
    "从台面上取走携带意象：{item}。": "Taken from the platform (carried image): {item}.",
    # ---- o 键目标辅助 / 瞄准辅助 ----
    "辅助": "Assist",
    " · 寻路辅助已开启": " · path assist on",
    "寻路辅助已开启（悬停地图显示路径）": "Path assist on (hover the map to see the route)",
    " · 辅助瞄准中": " · aim assist",
    "视野内没有可以辅助瞄准的失控意识。": "No rogue consciousness in sight to assist aiming at.",
})
from .data.npcs import EN_NPC_GIFT_REPLIES
EN.update(EN_NPC_GIFT_REPLIES)

LANGUAGE_PACKS: dict[str, dict[str, str]] = {
    "zh": {},
    "en": EN,
}
from .i18n_puzzles_en import EN_PUZZLES  # noqa: E402
EN.update(EN_PUZZLES)
from .i18n_vaults_en import EN_VAULTS  # noqa: E402
EN.update(EN_VAULTS)
from .i18n_enemy_skills_en import EN_ENEMY_SKILLS  # noqa: E402
EN.update(EN_ENEMY_SKILLS)

# Bilingual expansion copy is stored with the canonical item data. Only reviewed
# non-empty English fields enter the language pack; unfinished rows stay visible
# in Chinese until their translations are complete.
from .data.expansion.catalog import ENTRIES as _ITEM_EXPANSION_ENTRIES  # noqa: E402
for _entry in _ITEM_EXPANSION_ENTRIES:
    for _zh_field, _en_field in (("name_zh", "name_en"),
                                 ("description_zh", "description_en"),
                                 ("intro_zh", "intro_en")):
        if _entry.get(_zh_field) and _entry.get(_en_field):
            EN[_entry[_zh_field]] = _entry[_en_field]
    for _reading in (_entry.get("position_readings") or {}).values():
        if _reading.get("zh") and _reading.get("en"):
            EN[_reading["zh"]] = _reading["en"]
    # 记忆碎片的一句效果（面板直接显示 short）也是目录里的双语内容。
    _effect = _entry.get("effect") or {}
    if isinstance(_effect, dict) and _effect.get("short_zh") and _effect.get("short_en"):
        EN[_effect["short_zh"]] = _effect["short_en"]
from .data.epilogue_upgrade import TEXT as EPILOGUE_UPGRADE_TEXT
EN.update({pair[0]:pair[1] for pair in EPILOGUE_UPGRADE_TEXT.values()})
from .i18n_epilogue_en import EN_EPILOGUE  # noqa: E402
EN.update(EN_EPILOGUE)
from .data.realm_challenges import TEXT as REALM_CHALLENGE_TEXT
EN.update({pair[0]: pair[1] for pair in REALM_CHALLENGE_TEXT.values()})
from .i18n_content_en import EXTENSION_V2_EN, EXTENSION_V2_MESSAGES_EN  # noqa: E402
EN.update(EXTENSION_V2_EN)
EN.update(EXTENSION_V2_MESSAGES_EN)
from .i18n_content_en import CATALOG_NPC_EN  # noqa: E402
EN.update(CATALOG_NPC_EN)
from .i18n_content_en import FACTIONS_EN  # noqa: E402
EN.update(FACTIONS_EN)
from .i18n_content_en import TRAVEL_EN  # noqa: E402
EN.update(TRAVEL_EN)
from .i18n_content_en import JOURNAL_EN  # noqa: E402
EN.update(JOURNAL_EN)
# 篡改系统（2026-10-12）：混乱度档位、风险事件反馈、漏字者与「吞音」文本。
from .i18n_tamper_en import EN_TAMPER  # noqa: E402
EN.update(EN_TAMPER)
# 关键任务对象保护矩阵（2026-10-17）：地图篡改拒绝抹除时的可读理由。
from .i18n_tamper_protection_en import EN_TAMPER_PROTECTION  # noqa: E402
EN.update(EN_TAMPER_PROTECTION)
# 第三轮 i18n 覆盖率门补漏（2026-10-17）：惊散征兆、被打醒反馈与走廊改写提示。
from .i18n_late_gap_en import EN_LATE_GAP  # noqa: E402
EN.update(EN_LATE_GAP)
# 承载面归属与领取费用（2026-10-22）：医院工作台／图书馆书架的「归谁、取一件付什么」。
from .i18n_surface_en import EN_SURFACE  # noqa: E402
EN.update(EN_SURFACE)
# 选项区域的改后标签由变体片段拼成：中英文各自拼一次登记，避免翻译参与记账。
from .data.tampering import register_tamper_translations  # noqa: E402
register_tamper_translations()
EN["没有可到达的路径。"] = "No reachable path."
EN["封存记忆的蜡墙：遇火点燃，每回合消耗 2 点完整度，燃料耗尽后留下熔融蜡烛。"] = "A wax wall sealing memories: fire ignites it and consumes 2 integrity per round, leaving molten wax when its fuel runs out."
EN["齐踝的梦之草：可以踩过，遇液体消失；点燃后逐回合消耗燃料，约 2 回合烧尽。"] = "Ankle-high dream grass: walk over it freely; liquid removes it. Fire consumes its fuel each round, burning it away in about 2 rounds."

# ---- §8 S23 青灯入口（scene.lens_gate）----
EN.update({
    "守门的青灯": "gatekeeper lamp",
    "一盏青色的小灯悬在石台上方，灯罩里缺一块透镜；灯下的石阶通向一扇还没成形的门。":
        "A small cyan lamp hangs above a stone platform; a lens is missing from its housing. "
        "Below the lamp, stone steps lead to a door that has not yet taken shape.",
    "灯座上刻着一行：嵌进透镜，再喂它三件会消散的东西。":
        "A line is carved on the lamp base: fit in a lens, then feed it three things that will fade.",
    "青灯": "Cyan Lamp",
    "嵌进灯座的透镜": "Lens set in the lamp base",
    "付清的祭品": "Offerings paid",
    "已进入的门": "Entered door",
    "未开启": "Not yet opened",
    "等待支付": "Awaiting offerings",
    "开启": "Open",
    "已进入": "Entered",
    "已关闭": "Closed",
    "把灯塔透镜嵌进灯座（挑三件祭品）": "Fit the lighthouse lens into the lamp base (pick three offerings)",
    "走入镜中的门（进入梦中梦·玩具的回忆）":
        "Walk into the mirrored door (enter the dream-within-a-dream: Memories of Toys)",
    "青灯缺一块透镜：嵌进去，再从行囊里挑出三件易逝物或摄入物当祭品。":
        "The lamp is missing a lens: fit it in, then pick three perishables or ingestibles from your pack as offerings.",
    "只有门开着的时候才走得进去；这一走就进了位面。":
        "You can only walk in while the door is open; stepping through takes you into the realm.",
    "祭品还不够——要 {n} 件易逝物或摄入物。":
        "Not enough offerings — you need {n} perishables or ingestibles.",
    "{name}：透镜嵌进灯座，青灯转向你——挑三件会消散的东西。":
        "{name}: the lens seats into the lamp base, and the lamp turns toward you — pick three things that will fade.",
    "门在你身后合上了。": "The door shuts behind you.",
    "青灯吞下透镜与三件祭品——石台中央裂开了一道门。":
        "The lamp swallows the lens and three offerings — a door splits open at the center of the platform.",
    "祭品必须是恰好三件易逝物或摄入物。": "The offering must be exactly three perishables or ingestibles.",
    "行囊里没有灯塔透镜。": "There is no lighthouse lens in your pack.",
    "那处门已经不在这一层了。": "That door is no longer on this layer.",
    "青灯祭品": "Lamp Offerings",
    "挑三件会消散的东西，喂给守门的青灯。": "Pick three things that will fade and feed them to the gatekeeper lamp.",
    "已选 {n}/3": "Selected {n}/3",
    "↑↓ 选择 · 空格勾选 · Enter 确认 · Esc 取消": "↑↓ select · Space check · Enter confirm · Esc cancel",
})

# ---- §9 R03 留灯的避难圈（scene.lamp_refuge；quest.lamp_refuge）----
EN.update({
    # 场景名用裸小写名词（避免 describe 模板叠成「The The …」）。
    "留灯的避难圈": "lamp-lit refuge",
    "一圈反光的地面环着一座灯台，两侧各留一个可走的出口；灯台上压着一盏没点的留灯。":
        "A ring of reflective floor circles a lamp platform, with a passable exit left open on "
        "each side; an unlit reserve lamp rests on the platform.",
    "灯座刻着一行：先点起来，再让圈里清干净——灯只管一件事，圈里连着的安全才作数。":
        "A line is carved on the lamp base: light it first, then clear the ring — the lamp minds "
        "one thing, and only the safety held inside the ring counts.",
    # 布局键与具名开关显示名。
    "灯圈": "lamp ring",
    "西侧门": "west door",
    "东侧门": "east door",
    "点亮留灯": "lamp lit",
    "歇过的那一次": "the rest already taken",
    "修好的侧门": "repaired west door",
    # 命令 label／detail。
    "点亮留灯（把灯台激活）": "Light the reserve lamp (activate the platform)",
    "在圈里歇一会儿（心智 +4）": "Rest a while in the ring (Mind +4)",
    "在圈里歇一会儿（清醒 +4）": "Rest a while in the ring (Lucidity +4)",
    "修好侧门门轴，抬起挡板": "Fix the side-door hinge and lift the board",
    "花一点想象力点亮灯台：环线地面会反出光来。灯亮着，圈里的连续安全才作数。":
        "Spend a little imagination to light the platform: the ring of floor will reflect the "
        "glow. Only while the lamp burns does the ring's held safety count.",
    "灯亮、圈里没有火和危险气体时才能坐。只回心智，一次为限。":
        "You can only sit while the lamp burns and the ring holds no fire or dangerous gas. "
        "It restores mind only, once and once only.",
    "与「歇一会儿（心智 +4）」二选一：哪一种先坐下就算哪一种。":
        "Pick this or 'Rest a while (Mind +4)': whichever you sit down to first is the one you take.",
    "挡板落下就卡死在门槽里；挡板上正站着东西时不放。":
        "Once dropped the board jams in the door slot; it will not drop while something stands on it.",
    "随时可以把挡板抬回去。修门只动门，不动你歇过的那一次。":
        "You can lift the board back any time. Mending the door moves the door only, not the one "
        "rest you have taken.",
    # 命令预检拒绝文案。
    "留灯已经点着了，不用再点。": "The reserve lamp is already lit — no need to light it again.",
    "这一处你已经歇过了——一次为限。": "You have already rested here — once and once only.",
    "你此刻并不缺这些——歇着也回不了更多。":
        "You are not short of this right now — resting would restore nothing more.",
    "挡板本来就抬着——门没被堵上。": "The board is already lifted — the door is not blocked.",
    # 结算文案。
    "留灯亮了起来，灯圈的地面反出光（{n} 格）。":
        "The reserve lamp comes alight, and the ring of floor reflects its glow ({n} cells).",
    "你靠着灯台坐了一会儿：{stat} +{n}。":
        "You sit a while against the lamp platform: {stat} +{n}.",
    "{name}的挡板抬起来了。": "The {name}'s board has been lifted back up.",
    "{name}把一圈留灯围稳了：{n} 回合内新沾染的负面征兆会轻一些。":
        "{name} holds a ring of reserve light steady: for {n} rounds, newly caught negative "
        "portents bite a little less.",
    "避难圈的灯圈暗了下去，那点抵抗散了。":
        "The refuge ring's lamp dims, and that bit of resistance fades.",
    # 抵抗窗口征兆（面板展示）。
    "留灯的抵抗": "Reserve-light resistance",
    "留灯的避难圈把毒气挡在意识之外：新沾染的「中毒」时长减少 25%。":
        "The lamp-lit refuge keeps poison gas off the mind: a newly caught 'Poisoned' lasts 25% less.",
    "在留灯的避难圈里连续安全 3 回合":
        "Hold the lamp-lit refuge safe for 3 straight rounds",
    "留灯的抵抗：接下来 {n} 回合，新沾染的「{name}」时长减少 25%。":
        "Reserve-light resistance: for the next {n} rounds, a newly caught '{name}' lasts 25% less.",
    # 任务：名称／目标文本／提示／报酬／NPC 选项／解法名。
    "留灯的巡房": "Watch Round of the Lamp-lit Refuge",
    "把留灯的避难圈点起来，让环内连着 3 个世界回合没有火、没有失控意识踩进去":
        "Light the lamp-lit refuge and keep its ring free of fire and runaway awareness for "
        "3 straight world rounds",
    "第 2 层往下有一处留灯的避难圈。点亮灯台，把环内清干净（关掉火源、放气，"
    "或放下侧门挡板把东西挡在外头），连着三个世界回合别让失控意识踩进环里，回来销账。":
        "From layer 2 downward there is a lamp-lit refuge. Light the platform, clear the ring "
        "(douse the fires, vent the gas, or drop the side-door board to keep things out), and for "
        "three straight world rounds let no runaway awareness set foot in the ring — then come "
        "back and settle the order.",
    "一份补给＋避难圈使用权": "A supply plus use of the refuge",
    "一次夜诊护理": "One night-clinic treatment",
    "接取任务：留灯的巡房": "Take the task: Watch Round of the Lamp-lit Refuge",
    "销账：避难圈的灯点着了（要一份补给）": "Settle: the refuge lamp is lit (want a supply)",
    "销账：避难圈的灯点着了（要一次夜诊护理）":
        "Settle: the refuge lamp is lit (want a night-clinic treatment)",
    "环境修复": "Environment restored",
    "还差：把{name}点亮、环内清干净，让{zone}连着 {n} 个世界回合"
    "没有火、没有失控意识踩进去。":
        "Still missing: light the {name} and clear the ring, so that no fire and no runaway "
        "awareness sets foot in the {zone} for {n} straight world rounds.",
})

LANGUAGE_CHOICES: tuple[str, ...] = ("zh", "en")

LANGUAGE_LABELS: dict[str, str] = {"zh": "中文", "en": "English"}

# Additional authored realm vocabulary.
EN.update({})

from .i18n_realms import EN_REALMS
for _realm_key, _realm_value in EN_REALMS.items():
    EN.setdefault(_realm_key, _realm_value)

# ---- 位置语义装备的句子条件/事件短语（equipment.sentence_prose）----
EN.update({
    "没有附加条件": "No extra condition",
    "目标已有附着征兆": "Target already has an attached portent",
    "作用位置能够导电": "The target cell conducts",
    "作用位置有光且视线可达": "The target cell is lit and in sight",
    "作用位置有可燃材料": "The target cell has flammable material",
    "作用位置没有可燃材料": "The target cell has no flammable material",
    "作用位置有液体": "The target cell has liquid",
    "作用位置没有液体": "The target cell has no liquid",
    "目标带着折射印记": "The target carries a refraction mark",
    "目标没有折射印记": "The target has no refraction mark",
    "暂不支持这个条件": "This condition is not supported yet",
    "暂不支持的事件：{event}": "Unsupported event: {event}",
    "以下条件没有同时满足：{conditions}": "Not all of these conditions hold: {conditions}",
    "想象力高于 {n}": "imagination is above {n}",
    "想象力尚未耗尽": "imagination is not depleted yet",
    "目标没有附着征兆": "Target has no attached portent",
    "作用位置不能导电": "The target cell does not conduct",
    "作用位置没有光照或视线不可达": "The target cell is unlit or out of sight",
    "这个条件没有满足": "This condition is not met",
    "目标": "the target",
    "附加效果": "side effect",
    "以附加效果": "with the side effect",
    "其中的材料": "the material inside",
    "没有意识体的留白格": "a blank cell with no consciousness",
    "本次瞄准的位置": "the currently aimed cell",
    "这行暂未成句。": "This clause is not a sentence yet.",
    # ---- 未完成任务钉底 + 接取上限（2026-10-12）----
    "未完成任务：": "Open tasks: ",
    "手头已经挂着 {n} 单没交的任务——先交付或放弃一单再来。": "You already have {n} undelivered tasks - deliver or drop one first.",
    "进行中": "in progress",
    "待交付": "ready to deliver",
    "并非同时满足：{conditions}": "NOT all of: {conditions}",
    # ---- 光标区域切换（/ 键，2026-10-12）----
    "区域": "Zone",
    "光标区域：地图（方向键移动，WASD 动面板）": "Cursor zone: map (arrows move, WASD drives panel)",
    "光标区域：右侧面板（方向键/WASD 都动面板，←→ 切页）": "Cursor zone: side panel (arrows/WASD drive panel, left/right switch pages)",
    "光标区域：左侧浮层": "Cursor zone: left overlay",
})

# 主梦技能的玩家说明与条件。
from .data.skill_prose import EN_SKILL_PROSE
EN.update(EN_SKILL_PROSE)
EN["作用说明"] = "Effect details"
EN.update({
    '空手': 'Empty hands',
    '手上：{held}': 'Held: {held}',
    '工具：{tool}': 'Tool: {tool}',
    '光标 ({x},{y})': 'Cursor ({x},{y})',
    '旋转 {rotation}°': 'Rotation {rotation}°',
    '效果明细（确认后生效）': 'Effect details (after confirmation)',
    '第 {rows} 行 · {status}': 'Row {rows} · {status}',
    '盘上意象': 'On the board',
    '行囊意象': 'In the pack',
    '方向移动 · a拿放 · 空格取选中 · ,/.换项 · r旋转\nx拆除 · z功能词 · v详情 · A安置 · Enter确认 · Esc放回/取消':
        'Arrows move · A place/lift · Space pick · ,/. select · R rotate\nX remove · Z words · V details · Shift+A auto · Enter apply · Esc back',
})
EN.update({
    '这份赠品已经领过了。': 'You have already claimed this gift.',
    '这一局已经结束。': 'This run has ended.',
    '掌心的劲道': 'Palm strength',
    '这位稳定意识的免费赠品已经领完了，仍可交易或交谈。': 'This stable consciousness has no free gifts left; trades and conversation remain available.',
    '免费赠品：还可领取 {n} 项': 'Free gifts: {n} claims remaining',
    '买他一页手稿（3 件消耗品）': 'Buy a manuscript page (3 consumables)',
    '用 3 件消耗品换定金': 'Trade 3 consumables for a deposit',
})
from .data.environment_prose import EN_ENVIRONMENT_PROSE
EN.update(EN_ENVIRONMENT_PROSE)

from .data.item_prose import EN_ITEM_PROSE
EN.update(EN_ITEM_PROSE)

from .data.item_prose import EN_ITEM_EFFECTS
from .data.items import ITEM_DEFINITIONS as _PROSE_ITEM_DEFINITIONS
EN.update({_PROSE_ITEM_DEFINITIONS[key]['effect_description']: value
           for key, value in EN_ITEM_EFFECTS.items()})

from .data.realm_item_prose import REALM_ITEM_PROSE, REALM_ITEM_EFFECTS, EN_REALM_ITEM_EFFECTS
EN.update({zh: en for zh, en in REALM_ITEM_PROSE.values()})
EN.update({REALM_ITEM_EFFECTS[key]: value for key, value in EN_REALM_ITEM_EFFECTS.items()})

from .data.identity_prose import IDENTITY_PROSE, EN_IDENTITY_PROSE
from .data.dream_types import IDENTITY_DESCRIPTIONS, IDENTITY_RULE_DESCRIPTIONS
EN.update(EN_IDENTITY_PROSE)
from .i18n_system_roles_en import EN_SYSTEM_ROLES
EN.update(EN_SYSTEM_ROLES)
from .i18n_origin_course_en import EN_ORIGIN_COURSE
EN.update(EN_ORIGIN_COURSE)
from .i18n_npc_gaps_en import EN_NPC_GAPS
EN.update(EN_NPC_GAPS)
from .i18n_insight_memory_gaps_en import EN_INSIGHT_MEMORY_GAPS
EN.update(EN_INSIGHT_MEMORY_GAPS)
from .i18n_stat_names_en import EN_STAT_NAMES
EN.update(EN_STAT_NAMES)
from .i18n_concurrent_gaps_en import EN_CONCURRENT_GAPS
EN.update(EN_CONCURRENT_GAPS)
from .i18n_terrain_preview_en import EN_TERRAIN_PREVIEW
EN.update(EN_TERRAIN_PREVIEW)
EN.update({IDENTITY_DESCRIPTIONS[key]: prose[1] + '\nEffect: '
           + EN[IDENTITY_RULE_DESCRIPTIONS[key]].split('. ', 1)[1]
           for key, prose in IDENTITY_PROSE.items()})

# Shared player controls and QoL feedback.
EN.update({
    '操作与帮助': 'Actions and help', '全部注释': 'All notes', '单条注释点击': 'Click to expand one note',
    '收纳': 'Collect', '回应': 'Interact', '光标区域': 'Cursor zone', '光标锁定': 'Cursor lock',
    '原序': 'Original', '名称': 'Name', '类别': 'Category', '全部': 'All',
    '搜索': 'Search', '筛选': 'Filter', '排序': 'Sort', '全部注释': 'All notes',
    '当前注释': 'Current note', '适合屏幕': 'Fit map', '重置缩放': 'Reset zoom',
    '全选拾取': 'Select all', '确认祭品': 'Offer', '取消祭品': 'Cancel offer',
    '—— 操作帮助 ——': '-- Controls --',
    '方向键/小键盘：地图移动；WASD：面板选择；/ 切换焦点区域': 'Arrows/numpad: move; WASD: panel; /: focus zone',
    '鼠标左键：选择/行动；右键：详情；中键/Alt+左键：固定/快捷目标': 'Left click: select/act; right: details; middle/Alt+left: pin/shortcut',
    'Alt+E：展开当前条目；Alt+F：行囊搜索；Alt+L：行囊筛选；Alt+R：行囊排序': 'Alt+E: expand entry; Alt+F: search pack; Alt+L: filter; Alt+R: sort',
    'Alt+0：重置地图缩放；Alt+9：适合屏幕；F10：保存退出': 'Alt+0: reset zoom; Alt+9: fit map; F10: save and quit',
    '瞄准时 O：切换合法敌人；Tab：自由落点；Enter：确认；Esc：取消': 'Aiming: O cycles valid enemies; Tab: free cursor; Enter: confirm; Esc: cancel',
    '自由落点：方向键/小键盘移动光标；Enter：确认落点': 'Free cursor: arrows/numpad move; Enter confirms the landing cell',
    '观察时 P：固定/取消固定当前格；Alt+P：添加/移除快捷目标': 'Observing: P pins/unpins this cell; Alt+P adds/removes a shortcut',
    '自动收纳：安全时收纳；有可见失控意识时暂停，携带意象始终手动选择。': 'Auto-collect pauses near visible hostile minds; carried images always require manual selection.',
    '对象已经改变，本次确认已取消。': 'The object changed; confirmation cancelled.',
    '删除存档槽 {slot}？': 'Delete save slot {slot}?',
    '这个存档槽是空的。': 'This save slot is empty.',
    '此操作不可恢复。默认取消；选择确认后才删除。': 'Deletion is permanent. Cancel is selected by default.',
    '角色：': 'Identity: ', '身份未记录': 'Identity not recorded', '未记录': 'Not recorded',
    '本局：': 'Run: ', '梦层：': 'Layer: ', '回合数：': 'Turn: ', '预览来源：': 'Preview source: ',
    '存档内容无法预览；请核对槽位与文件后再决定。': 'Preview unavailable; check the slot and file before deleting.',
    '请先确认或取消当前选择。': 'Confirm or cancel the current choice first.',
    '确认使用 {name}？': 'Use {name}?',
    '会消耗物品或使用次数，并按物品规则消耗行动。取消不消耗。': 'Consumes an item or a use, and its normal action cost. Cancel is free.',
    '请确认使用。': 'Confirm use.', '请确认选择。': 'Confirm choice.',
    '确认这项选择？': 'Confirm this choice?',
    '此项会留下永久结果，确认后执行。': 'This choice has a permanent result.',
    '当前筛选没有可使用的物品。': 'No usable items match the current filter.',
    '搜索行囊：名称或物品标识；Enter/Esc 返回列表': 'Search pack by name or ID; Enter/Esc returns to the list',
    '放弃委托？': 'Abandon this task?',
    '不领取报酬，恢复一个委托名额。': 'No reward; frees one task slot.',
    '这项委托已经满足交付条件。': 'This task is already ready to deliver.',
    '已放弃': 'Abandoned', '放弃委托（不领取报酬，恢复名额）': 'Abandon task (no reward; frees a slot)',
    '位面下潜手续（不可放弃）': 'Realm descent checklist (cannot be abandoned)',
    '交付人失联：{reason}；可放弃委托恢复名额。': 'Giver unavailable: {reason}; abandon to free a slot.',
    '档案缺失': 'record missing', '已经离世': 'deceased', '所在位面已关闭': 'realm closed',
    '借书卡': 'Library card', '批注': 'Margin note', '目录机关': 'Catalogue mechanism',
    '病历夹': 'Chart folder', '叫号屏': 'Queue display', '一处设施': 'One facility',
    '完成本层解谜，并与守门人交谈': 'Solve this floor and speak to the keeper',
    '观察：方向键移动目光；Enter 前往；右键/单引号详情；Esc 返回': 'Observe: arrows move cursor; Enter walks; right click/quote: details; Esc returns',
    '右栏': 'Panel', '地图': 'Map', '焦点：{focus} · / 切换': 'Focus: {focus} · / switches',
    'Enter：所选条目': 'Enter: selected entry', 'Enter：脚下行动': 'Enter: act here',
    '待保存': 'Unsaved', '已保存': 'Saved', '自由落点': 'Free cursor', '未锁定': 'No lock',
    '一次性发射': 'One-use shot', '已失效语句': 'Expired sentence', '语句': 'Sentence',
    '瞄准：{action} · 射程 {distance} · {name}': 'Aim: {action} · range {distance} · {name}',
    '投出物品 1 件': 'Throws 1 item', '消耗物品 1 件': 'Consumes 1 item',
    '消耗工具 1 件': 'Consumes 1 tool', '消耗聚合弹 1 发': 'Consumes 1 charge',
    '想象力 {cost}': 'Imagination {cost}',
    '方向键落点 · O 换目标 · Enter 确认 · Esc 取消': 'Arrows: cursor · O: target · Enter: confirm · Esc: cancel',
    '方向键落点 · Tab 返回方向 · Enter 确认 · Esc 取消': 'Arrows: cursor · Tab: direction mode · Enter: confirm · Esc: cancel',
    'O 换敌 · Tab 自由落点 · 方向键/Enter 确认 · Esc 取消': 'O: enemy · Tab: free cursor · arrows/Enter: confirm · Esc: cancel',
    '确认替换现实洞察？': 'Replace this insight?', '确认替换记忆碎片？': 'Replace this memory?',
    '原有洞察会被替换。取消保留待选内容，不消耗行动。': 'Replaces the old insight. Cancel keeps the pending choice and costs no action.',
    '原有碎片及其效果会被替换。取消保留待选内容，不消耗行动。': 'Replaces the old memory and its effects. Cancel keeps the pending choice and costs no action.',
    '待替换对象已经改变。': 'The pending replacement changed.',
    '前路受到阻挡，自动行走已停止。': 'The route is blocked; automatic walking stopped.',
    '无法到达那个位置；请换一个落脚点。': 'That cell cannot be reached; choose another destination.',
    '推错了？回来与我交谈，选择重置本层机关。': 'Pushed the wrong way? Speak to me and choose to reset this floor.',
    '左键相邻格行动；远处左键逐步寻路。右键格子详情，中键固定目标。Alt+左键加入快捷/固定。滚轮滚动记录。': 'Left click acts nearby or walks to a distant cell. Right click: cell details. Middle: pin. Alt+left: shortcut/pin. Wheel: log.',
})

# 地势观察层与局部查看（docs §15.4—§15.5）。
from .i18n_elevation_en import EN_ELEVATION  # noqa: E402
EN.update(EN_ELEVATION)

# 材料反应配方（2026-10-22，E2 运行期文案审计）：播报走 tr(recipe.message)、
# 图鉴说明走 tr(recipe.note)，静态字面量扫描看不到这两条路径。
from .i18n_reactions_en import EN_REACTIONS  # noqa: E402
EN.update(EN_REACTIONS)

# A2 新增十件（2026-10-22）：物品名／描述、图鉴作用行、运行期提示。
from .i18n_deployables_en import EN_DEPLOYABLES  # noqa: E402
EN.update(EN_DEPLOYABLES)

# 图鉴字段补漏（2026-10-25）：扩展包装备的「作用」行、疗养院主动技能名、
# 弹体构想名与图书馆专属构想说明——这些值都走 tr，但英文包此前没有登记。
from .i18n_codex_en import EN_CODEX  # noqa: E402
EN.update(EN_CODEX)

# 扩展包装备的运行期反馈与六主题奖励选项（2026-10-25）：六主题实现成批落地
# 时只写了中文成品句，tr() 模板与事件选项标签都没登记英文。
from .i18n_expansion_gaps_en import EN_EXPANSION_GAPS  # noqa: E402
EN.update(EN_EXPANSION_GAPS)

# 可穿行植物地形（2026-10-27）：植物释出/格子详情/拔除确认/催生枯萎的补齐英文。
from .i18n_plant_en import EN_PLANT  # noqa: E402
EN.update(EN_PLANT)

# 书库散页构想的施放反馈模板由 i18n_realms.EN_REALMS 单独持有，不在这里重复一份。

# ---- 混乱极高专属异象（2026-10-27 玩家需求）----
# 三只异象（嗔影/空心者/伪光者）及其六个强力技能、召唤提示与结算文案。
# 异象名/描述走 tr(变量)（不经过 AST 静态扫描），仍然必须在这里登记，
# 否则英文渲染会直接露出中文（见 tests/test_i18n_coverage.py 的取值域枚举）。
EN.update({
    "嗔影": "Wrath Shade",
    "空心者": "Hollow One",
    "伪光者": "False Light",
    "混乱意象": "Chaos Image",
    "它从你没说出口的那句重话里立起来，轮廓边缘一直在发烫。":
        "It stands up out of the harsh sentence you never said; the edge of its outline keeps smoldering.",
    "胸口的位置是一个能看见后面的洞；它靠近时，先拿走你的一小块。":
        "Where its chest should be there is a hole you can see through; when it comes close, it takes a small piece of you first.",
    "它顶着一圈过亮的光，光照到的地方都变得不太可信。":
        "It wears a ring of light that is too bright; wherever the light falls, things stop being trustworthy.",
    "嗔线：它把没消下去的火拉成一条线，沿视线烧过来。":
        "Wrath Line: it pulls the fire it never put out into a line and burns along its sightline.",
    "掏空之吸：它隔空对你吸气，把自己缺的那一块补回去。":
        "Hollowing Draw: it breathes in across the air and fills the part of itself that is missing.",
    "伪光注视：它把光转到你身上，你看到的东西开始对不上号。":
        "False Light Gaze: it turns its light on you and what you see stops matching up.",
    # 技能名
    "嗔线": "Wrath Line",
    "嗔爆": "Wrath Burst",
    "掏空之吸": "Hollowing Draw",
    "空腹洞开": "Hollow Gorge",
    "伪光注视": "False Light Gaze",
    "伪光轮": "False Light Halo",
    # 技能效果／条件／反制（图鉴详情与观测共用）
    "沿视线拉出一条至多十三格的炽线，命中一次心智创伤；基础创伤 10，深层会顶到强烈异象的单次上限。":
        "Pulls a burning line up to thirteen cells along its sightline for one mind trauma; base trauma 10, capped at the elite per-hit limit in deep layers.",
    "目标在视线内，且两人之间有可以落线的直线。":
        "Target in sight with a clear straight line between you.",
    "横移出线，或用墙体、实体遮挡。":
        "Step out of the line, or block it with a wall or a body.",
    "以自身为中心炸开半径两格的嗔火（十三格），命中一次清醒创伤；基础创伤 11，命中后把你掀开一格。":
        "Detonates wrath fire in a two-cell radius around itself (thirteen cells) for one lucidity trauma; base trauma 11, and knocks you back one cell on a hit.",
    "目标在视线内且距离不超过三格（火要够得着才起手）。":
        "Target in sight within three cells (it only ignites when the fire can reach).",
    "拉开到三格以外；火起手后停两拍再靠近。":
        "Open the distance past three cells; wait two beats after it ignites before closing in.",
    "沿直线隔空吸气，命中一次心智创伤（基础 9），并把自己缺的完整度吸回两点。":
        "Draws in along a straight line for one mind trauma (base 9) and pulls two integrity back into itself.",
    "横移出线；它吸空的那一下不会补满上限。":
        "Step out of the line; the draught will not take it back to full.",
    "在目标周围开一个半径两格的空洞（十三格），命中一次心智创伤（基础 8）并额外抹去两点想象力。":
        "Opens a hollow two cells wide around the target (thirteen cells) for one mind trauma (base 8) and wipes away two imagination.",
    "目标在视线内。": "Target in sight.",
    "走出空洞范围；空洞只开两拍。":
        "Walk out of the hollow; it only stays open two beats.",
    "把过亮的光转到目标身上：挂上「失焦」（视野 −1，两回合）并抹去三点想象力。":
        "Turns its too-bright light on the target: applies Blurred (sight −1 for two rounds) and wipes away three imagination.",
    "在它落光前离开原地；失焦最多把视野减到 3。":
        "Leave the cell before the light lands; Blurred never drops sight below 3.",
    "在最亮处铺下一圈半径两格的迟帧光场（五格）；踩进去的脚步会被光缠住（移动额外耗时 +0.2）。":
        "Spreads a slow-frame light field in a two-cell radius around the brightest spot (five cells); stepping inside tangles your step (+0.2 move time).",
    "目标若在视线内；不在视线内时按最后目击位置落地。":
        "Lands on the target if in sight, otherwise on the last known position.",
    "绕开光场，或等光自己灭掉（五回合）。":
        "Walk around the field, or wait for the light to burn out (five rounds).",
    # 召唤提示与技能结算文案
    "混乱在你改过的句子边上站起一个剪影——{name}。":
        "A silhouette rises beside the sentence you just rewrote — {name}.",
    "混乱在一个空处聚拢成形——{name}已经站在你附近。":
        "Chaos gathers into shape in an empty spot — {name} is already near you.",
    "梦层深处的混乱挤成一个人形——{name}在你身边成形。":
        "The chaos deep in the dream layer squeezes into a human shape — {name} forms beside you.",
    "嗔爆在你身边炸开——你已经在火外。":
        "The wrath burst detonates around you — you are already outside the fire.",
    "嗔影自燃了一瞬——嗔爆把你卷进去（{channel} {power}）。":
        "The wrath shade burns for an instant — the burst sweeps you in ({channel} {power}).",
    "空心者隔空吸了一口——线已经偏了。":
        "The Hollow One draws breath through the air — the line has already drifted.",
    "空心者把你的力气吸了过去（心智 {power}；它补回 {healed} 点完整度）。":
        "The Hollow One pulls your strength away (mind {power}; it regains {healed} integrity).",
    "空洞在你刚才站着的地方张开，什么也没卷住。":
        "A hollow opens where you just stood and closes on nothing.",
    "空腹洞开：周围的想象被吸进去一点（心智 {power}；想象力 −{n}）。":
        "Hollow gorge: the surrounding imagination is drawn in (mind {power}; imagination −{n}).",
    "伪光落在你刚才站的地方——光没有认住你。":
        "The false light falls where you just stood — it did not catch you.",
    "伪光贴上来了，但你的轮廓没有接住它。":
        "The false light clings to you, but your outline will not hold it.",
    "伪光者盯住你：视野 −1（失焦），想象力 −{n}。":
        "The False Light fixes on you: sight −1 (blurred), imagination −{n}.",
})
