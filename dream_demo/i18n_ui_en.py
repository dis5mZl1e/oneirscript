"""英文语言包 · 界面补全 / 运行消息 / 地点名。

三部分：

- ``EN_UI``      —— 设置页、面板、配色表等**界面词条**（含新加的观测/详情面板）。
- ``EN_MESSAGES``—— 事件记录里**运行时生成**的提示。带 ``{占位符}`` 的条目由
  ``tr(template, **kwargs)`` 插值，占位符名与调用点一一对应。
- ``EN_PLACES``  —— 层型 / 楼层修饰符 / vault 模板名（层型与修饰符会显示在状态栏）。

键仍是中文原文；未登记的键在 ``tr()`` 里原样返回。
"""

from __future__ import annotations

EN_UI: dict[str, str] = {
    '这件显化物尚未到可获得的梦层。': 'This manifestation is not available at this dream depth.',
    '这件显化物只能从指定挑战获得。': 'This manifestation can only be earned from its designated challenge.',
    '本局已经获得过这件限定显化物。': 'This run has already received this limited manifestation.',
    '限定显化物已补记本局发放记录：现有数量原样保留，丢弃或使用不会重置获取上限；载入前梦痕已备份。':
        'Limited-item awards have been recorded for this run. Existing quantities are unchanged; discarding or using them does not reset the award limit. Your save was backed up before loading.',
    '{item}的账单到了：{resource} −1。': '{item} installment due: {resource} −1.',
    '本次新增心智债务 8 点，10 回合分期；登记时应付心智合计 {n} 点（含旧债），不覆盖其他账单。':
        'Adds 8 mind debt over 10 rounds. Total mind scheduled on ingestion: {n}, including existing bills; other schedules remain unchanged.',
    '心智账单': 'Mind installments',
    '未竟的句点：尚欠心智 {n} 点，按各份原时刻独立分期支付，不可用新药覆盖。':
        'Unfinished Full Stop: {n} mind still owed. Each dose keeps its own installment schedule; a new dose cannot erase it.',
    '速度征兆按既定上下限汇总，限时物品额外修正':
        'Omen speeds use their established limits; timed items apply separately.',
    '征兆速度倍率叠乘并受上下限约束，限时物品另修正；行动耗时 = 基础耗时 / 该倍率':
        'Omen speed multipliers stack within their limits; timed items apply separately. Action time = base time / this multiplier.',
    '完成握手后，8 回合内行动耗时 ×0.8，随后 4 回合 ×1.2；期间不能再次启动，不刷新构想冷却。':
        'After the handshake, actions take ×0.8 time for 8 rounds, then ×1.2 time for 4 rounds. Cannot restart during either phase; construct cooldowns keep running normally.',
    '56k 猫仍在缓冲，暂时不能再次启动。': 'The 56k Modem is still buffering and cannot restart yet.',
    '56k 猫：缓冲加速': '56k Modem: buffered speed',
    '56k 猫：缓冲迟滞': '56k Modem: buffer recovery',
    '缓冲加速': 'Buffered speed',
    '缓冲迟滞': 'Buffer recovery',
    '56k 猫：行动耗时 ×0.8，结束后进入 4 回合缓冲迟滞。':
        '56k Modem: actions take ×0.8 time, followed by 4 rounds of buffer recovery.',
    '56k 猫：行动耗时 ×1.2，等待缓冲恢复。': '56k Modem: actions take ×1.2 time while the buffer recovers.',
    '想象力立刻沸腾，清醒度随后分期偿还。每份独立支付 5 点清醒度，10 回合还清，重复服用不覆盖旧债。':
        'Imagination comes to the boil, with lucidity paid back later: each dose costs 5 lucidity over 10 rounds and does not replace earlier bills.',
    '本次新增清醒度债务 5 点，10 回合分期；登记时应付合计 {n} 点（含旧债），各份按原时刻独立扣款。':
        'Adds 5 lucidity debt over 10 rounds. Total scheduled on ingestion: {n}, including existing bills. Each dose keeps its own due dates.',
    '尚欠清醒度 {n} 点（各份独立结算）。':
        'Lucidity still owed: {n} (each dose is paid separately).',
    '{item}的账单到了：清醒度 −1。': '{item} installment due: lucidity −1.',
    '浓缩咖啡因账单': 'Espresso installment',
    '贤者之粉账单': 'Sage Powder installment',
    '未竟的句点账单': 'Unfinished Full Stop installment',
    '药物债务已改为逐份独立结算：只继承尚未支付的期数和原扣款时刻，不补收过去的账单；载入前梦痕已备份。':
        'Medicine debt now keeps a separate schedule for each dose. Only unpaid installments and their due dates were carried over; no past bills were added. Your save was backed up before loading.',
    '图像：边缘标记；字符：加粗下划线；当前危险见下方状态。': 'Image: edge marks. Text: bold underline. Current hazards appear in the status below.',
    '技能预警': 'Skill warning', '电场': 'Electric field',
    '危险气体': 'Hazardous gas', '危险': 'Danger',
    '上边': 'Top edge', '右边': 'Right edge',
    '下边': 'Bottom edge', '左边': 'Left edge',
    '构想费用': 'Conception cost', '篡改费用': 'Tampering cost',
    '交易费用': 'Trade cost', '自然恢复': 'Natural recovery',
    '物品恢复': 'Item recovery', '场景恢复': 'Scene recovery',
    '派生恢复': 'Derived recovery', '剧情变化': 'Story change',
    '上限变化': 'Capacity change', '调试变化': 'Debug change',
    '环境影响': 'Environmental effect', '战斗创伤': 'Combat trauma',
    '资源已归零': 'Resource depleted', '达到上限': 'At capacity',
    '没有可恢复量': 'Nothing to restore',
    '自然心智恢复': 'Natural mind recovery',
    '分层观察 · Tab 切层 · 点击/Esc 返回': 'Layers · Tab: switch · Click/Esc: return',
    '无原生终端输出': 'No native terminal output',
    '图像地图输出失败；请按 F2 选择字符地图后继续。': 'Image output stopped. Press F2 and choose Character to continue.',
    '点击': 'Click',
    '地图显示': 'Map display',
    '地图显示 F2': 'Map mode F2',
    '默认观察层': 'Initial inspection layer',
    '分层观察': 'Layer inspection',
    '分层观察 F3': 'Layers F3',
    '完整键位表 Alt+H': 'Controls Alt+H',
    '综合': 'Composite',
    '地形': 'Terrain',
    '液体': 'Liquid',
    '气体': 'Gas',
    '声音线索': 'Sound clues',
    '已辨向的近期声响': 'Recent sound with known direction',
    '只知方向的声响': 'Sound known only by direction',
    '听界发声点': 'Listen-realm sound origin',
    '确认声源（保留 2 回合）': 'Confirmed source (kept 2 turns)',
    '当前选中的线索': 'Selected clue',
    '只标发声格，不照亮周围地形': 'Marks the sound cell only; the surroundings stay dark',
    '确认声源（循声定位）': 'Confirmed source (sound triangulation)',
    '听界标记（剩余 {n} 回合）': 'Listen-realm markers ({n} turns left)',
    '听界只记录该次声音的发生点，不检测安静目标，也不照亮周围。':
        'The listen realm records only where that sound occurred; it does not detect silent targets or light the surroundings.',
    '数字键或点击选择线索并在地图高亮；L 凝听一回合（确认后才会等待）。':
        'Digits or a click select a clue and highlight it on the map; L listens for one turn (waiting only happens after you confirm).',
    '隔墙入口：({x},{y})': 'Behind-wall entry: ({x},{y})',
    '多次响动': 'Multiple sounds',
    '强度：{strength}': 'Strength: {strength}',
    '强': 'Strong',
    '中等': 'Medium',
    '弱': 'Weak',
    '听诊器只对相邻实墙后的真实声音给入口与近距判断；远墙悬停不生效。':
        'The stethoscope gives an entry point and near-distance reading only for real sounds behind an adjacent solid wall; hovering distant walls does nothing.',
    '凝听一回合 · L / 点击': 'Listen one turn · L / click',
    '听界': 'Listen realm',
    '循声定位': 'Sound triangulation',
    '持续 3 回合：把实际传到你的声音临时标成发声格，只记该次声音的位置与时刻；不检测安静对象，也不照亮周围地形。起手自身产生 3 格声响。':
        'For 3 turns, sounds that actually reach you are temporarily marked at their origin, recording only that event\'s cell and time; silent objects are not detected and the surroundings are not lit. Activating it makes a noise of radius 3 at your position.',
    '听界展开：{turns} 回合内，传到你的声音会标出发声格。':
        'Listen realm opens: for {turns} turns, sounds that reach you mark their origin cell.',
    '凝听期间，对同一固定发声地点在不同真实时刻至少听见两次、每次接收余量 ≥4 时，把该地点标为「确认声源」，最近一次确认保留 2 回合；声音搬走后不跟随，也不认出生物身份。':
        'While listening, hearing the same fixed source at two different real turns with residual at least 4 marks it as a confirmed source, kept for 2 turns; a sound that moves is not followed, and the creature\'s identity is not revealed.',
    '返回地图': 'Return to map',
    '未知区域': 'Unexplored',
    '当前：': 'Current: ',
    'Tab / F3 切层；方向键观察；Enter 详情': 'Tab / F3: layer; arrows: look; Enter: details',
    '分层观察 · Tab 切层 · Esc 返回': 'Layers · Tab: switch · Esc: return',
    '↑↓ 选择 · Enter 确认 · Esc 返回': 'Up/Down: select · Enter: confirm · Esc: return',
    '当前终端不支持图像地图，请使用随包 WezTerm': 'Image maps require the bundled WezTerm',

    '确认删除': 'Confirm deletion',
    '移动与地图': 'Movement and map',
    '战斗': 'Combat',
    '观察与目标': 'Observe and target',
    '行囊与装备': 'Inventory and equipment',
    '界面与系统': 'Interface and system',
    '地图移动；小键盘 5 等待可在设置中关闭': 'Move; numpad 5 wait can be disabled in settings',
    '面板选择；方向主键可在设置中修改': 'Panel selection; directional keys are configurable',
    '下潜 / 上浮': 'Descend / ascend',
    '重置缩放 / 适合屏幕': 'Reset zoom / fit screen',
    '投掷；在面板中返回': 'Throw; return within panels',
    '行动或确认当前选择': 'Act or confirm the current selection',
    '瞄准时切换合法敌人': 'Cycle eligible enemies while aiming',
    '瞄准时进入自由落点': 'Choose a free target while aiming',
    '自由落点模式：移动光标': 'Move the free targeting cursor',
    '取消瞄准': 'Cancel aiming',
    '观察时前往光标位置': 'Travel to the observed position',
    '观察时固定或取消固定当前格': 'Pin or unpin the observed cell',
    '添加或移除快捷目标': 'Add or remove a quick target',
    '切换光标区域': 'Switch cursor area',
    '固定或快捷目标': 'Pin or quick target',
    '收纳 / 使用 / 回应': 'Pick up / use / interact',
    '丢下首件 / 装备首件': 'Drop first item / equip first item',
    '行囊筛选 / 排序': 'Filter / sort inventory',
    '全部注释 / 单条注释点击': 'All notes / individual note clicks',
    '打开联想盘': 'Open the association board',
    '盘内选择或移动光标': 'Select or move the board cursor',
    '确认当前盘内操作': 'Confirm the current board operation',
    '逐级返回；其余操作见盘内提示': 'Go back; other controls appear on the board',
    '对话中打开篡改面板': 'Open text tampering in dialogue',
    '打开或关闭完整键位表': 'Open or close the controls reference',
    '展开或收起底栏': 'Expand or fold the footer',
    '返回或打开菜单': 'Return or open the menu',
    '选择或行动 / 详情': 'Select or act / details',
    '滚动当前列表': 'Scroll the current list',
    '完整包已附 WezTerm 与字体；通过默认启动入口使用，兼容终端也可进入':
        'The full package includes WezTerm and fonts. Use the default launcher; other terminals also work.',
    '完整键位表': 'Controls reference',
    '完整键位表 · 点击 / Alt+H': 'Controls · click / Alt+H',
    '展开 ▼': 'Expand ▼',
    '收起 ▲': 'Fold ▲',
    '关闭 · Esc / Q': 'Close · Esc / Q',
    'Alt+H：完整键位表；Alt+Z：展开/收起底栏。': 'Alt+H: controls reference; Alt+Z: expand/fold footer.',
    '滚轮 / ↑↓ / PgUp / PgDn：滚动；Esc / Q 或关闭按钮：返回。': 'Wheel / arrows / PgUp / PgDn: scroll; Esc / Q or Close: return.',
    '终端兼容提示': 'Terminal compatibility',
    '当前使用兼容终端，游戏可正常进入；字体、emoji 或地图对齐可能有差异。完整包已附 WezTerm，重新使用默认启动入口即可，无需另行下载。':
        'You can play in this terminal, but fonts, emoji or map alignment may differ. The full package includes WezTerm; use the default launcher to switch. No separate download is needed.',
    "WezTerm 启动失败：{path}": "Failed to launch WezTerm: {path}",
    '保存失败，未重启：{reason}': 'Save failed; restart cancelled: {reason}',
    '终端配置失败：{reason}': 'Terminal configuration failed: {reason}',
    # 观测面板主动技能摘要（2026-10-09）：技能数值行 + 创伤渠道词。
    # 「心智/清醒」词键同时供 enemy_skills 命中消息的 {channel} 复用。
    "技能 ": "skill ",
    "特性 ": "trait ",
    "心智": "mind",
    "清醒": "lucidity",
    "创伤 无": "no trauma",
    "创伤 {channel} {value}": "trauma {channel} {value}",
    "冷却 {n} 回合": "cooldown {n} round(s)",
    # 主动技能观测补全（2026-10-10）：数值行参数 + 效果/条件/反制标签 +
    # 运行时冷却/蓄势状态行（各技能独立 CD，状态行报告「最早再起手」）。
    "蓄势 {n}": "wind-up {n}",
    "持续 {n} 回合": "lasts {n} round(s)",
    "恢复 {n} 回合": "recovery {n} round(s)",
    "距离 {n}": "range {n}",
    "效果": "Effect",
    "条件": "Condition",
    "反制": "Counter",
    "技能 蓄势中：「{skill}」剩 {n} 回合": "skill winding up: {skill}, {n} round(s) left",
    "技能 冷却中：最早 {n} 回合后再起手": "skill cooling down: next cast in {n} round(s)",
    "蓄势中：「{skill}」剩 {n} 回合": "winding up: {skill}, {n} round(s) left",
    "冷却中：最早 {n} 回合后再起手": "cooling down: next cast in {n} round(s)",
    # equipment/links.explain 的反应链解释（2026-10-09 补齐既有缺口）。
    "当{event}时，尝试{effect}。": "When {event}, attempt {effect}.",
    '我握着{item}': 'I wield {item}',
    '我收着{item}备用': 'I keep {item} in reserve',
    '我披着{item}': 'I wear {item}',
    '我系着{item}': 'I bind {item} to myself',
    '我带着{item}': 'I carry {item}',
    '我把{item}留作尚未写下的念头': 'I leave {item} as an unwritten thought',
    '我把{item}想成{meaning}': 'I imagine {item} as {meaning}',
    '一个安静的意象': 'a quiet image',
    '当我命中目标时': 'When I hit a target',
    '当我受到创伤时': 'When I suffer trauma',
    '当我接触液体或气体时': 'When I enter liquid or gas',
    '当我展开构想时': 'When I unfold a conception',
    '若触发位置能够导电': 'if the triggering place conducts electricity',
    '若想象力已落入留白的范围': 'if my imagination falls within the blank threshold',
    '我让{where}附近的湿润敌人受到微弱电击': 'I give a wet foe near {where} a faint electric shock',
    '我护住自己下一次受到的创伤': 'I soften the next trauma I suffer',
    '我把触发位置的液体引向较空的邻格': 'I guide liquid from the triggering place to an emptier neighbour',
    '我在{where}留下一点能燃烧的余温': 'I leave a little burning warmth at {where}',
    '我让{where}响起引人回头的轻声': 'I make a quiet sound at {where} that draws attention',
    '我把这一刻留住，两个回合后{effects}': 'I hold this moment and, two turns later, {effects}',
    '我空着双手，让梦暂时保持原样。': 'I keep my hands empty and let the dream rest.',
    '这一分句缺少「{meaning}」的意象，联想还不能发生。': 'This clause needs an image of {meaning} before it can respond.',
    '这个念头还没有写下，暂不影响梦境。': 'This thought is unwritten and has no effect yet.',
    '借用它的含义来联想，原本的装备效果暂时放下。': 'Borrow its meaning for a response; set its original equipment effect aside.',
    '收着备用，切换握持后才用它攻击。': 'Keep it in reserve; wield it to attack with it.',
    '攻击沿用这件武器的消耗': 'Attacks keep this weapon\'s costs',
    '持续生效，不额外消耗想象力': 'Ongoing, with no extra imagination cost',
    '想象力 {cost} · 共享冷却 {turns} 回合': 'Imagination {cost} · shared cooldown {turns} turns',
    "攻击等待确认。": "Attack awaiting confirmation.",
    "确认攻击？Y / Enter 确认\nN / Esc / Q 取消 · 8 秒后取消\n方向键或点击地图可取消并行动":
        "Attack? Y / Enter confirms\nN / Esc / Q cancels · expires in 8s\nArrows / map click cancel and act",
    '调律': 'Tuning',
    '身份': 'Identity',
    '记忆': 'Memory',
    '↑↓ 选择 · ←→ 调整 · Enter/空格选中 · 鼠标点击\nR 默认 · G 随机 · C 继续/入梦 · Esc 返回；灰项不可用':
        'Arrows select/adjust · Enter/Space select · Mouse click\nR default · G random · C next/dream · Esc back; grey = unavailable',
    '{item}只作意象，目前不提供线路语义，也不注册原效果。': '{item} is imagery only: it grants no circuit semantics or original effect.',
    # ---- 设置页：按键绑定的动作名（RESERVED_KEY_BINDINGS 的取值） ----
    "固定方向或等待键": "Fixed direction / wait keys",
    "等待动作": "Wait action",
    "瞄准动作": "Aim action",
    "收纳动作": "Pick-up action",
    "回应动作": "Respond action",
    "返回或投掷动作": "Back / throw action",
    "使用动作": "Use action",
    "层间移动": "Descend",
    "层间返回": "Backtrack",
    "现实洞察界面": "Insights panel",
    "观测录界面": "Observation panel",
    "操作界面": "Actions panel",
    "注释展开收起": "Toggle notes",
    # ---- 设置项 / 错误提示 ----
    "不能绑定空按键。": "Cannot bind an empty key.",
    "按键必须是单个可打印字符。": "The key must be a single printable character.",
    "该按键由{action}保留。": "That key is reserved for {action}.",
    "按键已用于{label}。": "That key is already used for {label}.",
    "未知设置项。": "Unknown setting.",
    "设置值无效。": "Invalid setting value.",
    "设置没有变化。": "Setting unchanged.",
    "该设置需要捕获一个按键。": "This setting needs a captured key.",
    "该设置不是按键绑定。": "This setting is not a key binding.",
    "正在等待输入：": "Waiting for input: ",
    # ---- 观测面板 / 详情面板 ----
    "耐久": "Integrity",
    "伤害": "Damage",
    "攻速": "Attack Speed",
    "移动": "Move",
    "视野": "Vision",
    "听觉": "Hearing",
    "创伤": "Trauma",
    "获得": "Gained",
    "快捷目标：": "Shortcuts: ",
    "—— 目标操作 ——": "—— Target Actions ——",
    "观测详情": "Anomaly Details",
    "未选择意象。": "No anomaly selected.",
    "物品": "Item",
    "物品已不在行囊中。": "The item is no longer in your bag.",
    "该意象此刻不在视野中。": "That anomaly is no longer in sight.",
    "状态": "State",
    "记忆槽": "Memory Slot",
    "资料异常": "Data anomaly",
    "滚轮或 ↑↓ 滚动 · Q/Esc 关闭": "Wheel or ↑↓ to scroll · Q/Esc to close",
    "第 {a}-{b}/{c} 行 · 滚轮或 ↑↓ 滚动 · Q/Esc 关闭":
        "Lines {a}-{b}/{c} · wheel or ↑↓ to scroll · Q/Esc to close",
    "↑↓ 在可选字段间移动光标（跳过介绍/空行），并随之滚动。":
        "↑↓ moves the cursor between selectable fields (skipping notes and blanks) and scrolls along.",
    # ---- 主页光标 / 图鉴方向键（←→ 选左右项、切分类） ----
    "←→ 选择选项 · ↑↓ 换行 · 左键点击进入 · D 删除":
        "←→ pick option · ↑↓ change row · left-click to enter · D delete",
    "左键点击进入，按 D 删除。": "Left-click to enter, D to delete.",
    "左键点击开始新游戏（Enter 不再开新游戏）。":
        "Left-click to start a new game (Enter no longer starts one).",
    "再次按 Enter 确认删除存档槽 {n}；按方向键取消。":
        "Press Enter again to delete save slot {n}; any arrow key cancels.",
    "←→ 切换分类 · ↑↓ 选择条目 · 滚轮浏览 · Q 返回分类":
        "←→ switch category · ↑↓ pick entry · wheel scroll · Q back",
    # ---- 警戒状态 ----
    "未察觉": "Unaware",
    "怀疑": "Suspicious",
    "警戒": "Alert",
    "追踪": "Tracking",
    # ---- 异象意图切换提示（docs/261021异象意图与行动切换提示设计.md §5） ----
    "开始怀疑": "Started suspecting",
    "开始调查": "Started investigating",
    "开始追踪": "Started tracking",
    "失去目标": "Lost the target",
    "开始逃离": "Started fleeing",
    "开始蓄力": "Began charging",
    "蓄力被打断": "Charge interrupted",
    "恢复硬直": "Entered recovery",
    "刚才切换：{label}": "Just switched: {label}",

    # ---- 聚合墙的观感变体（悬停「地板」名） ----
    "柔软聚合物": "Soft Aggregate",
    "粗糙聚合物": "Rough Aggregate",
    "反光聚合物": "Reflective Aggregate",
    "吸声聚合物": "Sound-absorbing Aggregate",
    "空白聚合物": "Blank Aggregate",
    "木质聚合物": "Wooden Aggregate",
    "海绵聚合物": "Sponge Aggregate",
    "金属聚合物": "Metal Aggregate",
    "灼热聚合物": "Scorching Aggregate",
    "梦境绒毯": "Dream Velvet",
    "冰面": "Ice Sheet",
    "星图地": "Star Chart Ground",
    "书页地": "Page Ground",
    "月壤": "Moon Soil",
    "棋盘格地板": "Checkerboard Floor",
    "绝热层": "Thermal Barrier",
    "压电地板": "Piezo Floor",
    "石墨烯晶格": "Graphene Lattice",
    "玉米淀粉墙": "Cornstarch Wall",
    "余烬灯盏": "Ember Lamp",
    "嵌壁梦灯": "Dream Niche Lamp",
    "弧光灯架": "Arc Lamp Rig",
    "余烬的暖味": "the warm smell of embers",
    "灯罩里透出一口暖息": "a breath of warmth seeps through the lampshade",
    "臭氧与金属的焦味": "the acrid tang of ozone and hot metal",
    "这盏灯靠燃烧发光——点火或灭火，而不是拨开关。":
        "This lamp burns to give light — ignite or extinguish it, not flick a switch.",
    "灯架的电源接在电路上，这里没有可以拨的开关。":
        "The lamp rig draws power from a circuit; there is no switch to flick here.",
    "液氦": "Liquid Helium",
    "铃兰薄荷": "Lily-of-the-Valley Mint",
    "琥珀蕨": "Amber Fern",
    "忘忧雏菊": "Carefree Daisy",
    "彩玻菌": "Stained-Glass Mushroom",
    "低语蕨": "Whispering Fern",
    # ---- 其它 ----
    "想象创伤": "Imagination Trauma",
    "接触创伤": "Contact Trauma",
    "可下潜": "Descend ready",
    "中文": "Chinese",
    "我": "Me",
    # ---- 格子详情面板（右键格子 / 观察模式按 '） ----
    "格子详情": "Cell Details",
    "未选择格子。": "No cell selected.",
    "第 {n} 层": "Layer {n}",
    "视野外": "Out of sight",
    "凭记忆只能认出地面与墙体，其余内容以 ? 代替。":
        "Memory only preserves the floor and walls here; everything else shows as ?",
    "地板": "Floor",
    "表面": "Surface",
    "高处": "High",
    "空中": "Air",
    "固体": "Solid",
    "液体": "Liquid",
    "气体": "Gas",
    "植物": "Plant",
    "高度": "Height",
    "可徒手推倒": "can be pushed over bare-handed",
    "不遮挡视线": "does not block sight",
    "发光": "glowing",
    "抗液抗火": "liquid-proof & fireproof",
    "接触": "contact",
    "吸入": "inhalation",
    "生物": "Creature",
    "你自己": "yourself",
    "（{kind}）": " ({kind})",
    "掉落物": "Drop",
    "事件": "Event",
    "联想反馈·{label}：在 {x},{y} 留下一点余温（强度 {strength}）。":
        "Link feedback · {label}: leaves an ember at {x},{y} (strength {strength}).",
    "联想反馈·{label}：{x},{y} 响起一次轻声（{reached} 个失控意识转头）。":
        "Link feedback · {label}: a whisper at {x},{y} turns {reached} uncontrolled minds.",
    "联想反馈·{label}：把这次事件存了下来，{due} 回合时释放。":
        "Link feedback · {label}: stores this event and releases it on turn {due}.",
    # ---- 2026-10-15 补全：controls.py 动作标签 + 瞄准/委托日志/Ctrl+Q 界面串
    # （并行会话加的 UI 词条漏了 EN，test_i18n_coverage 逮出）。
    "瞄准": "Aim",
    "辅助瞄准": "Assisted aim",
    "返回或投掷": "Back / throw",
    "保存退出": "Save & Quit",
    "输入物品名称；Enter 确定，Esc 取消": "Type an item name; Enter to confirm, Esc to cancel",
    "委托日志 · J": "Task log · J",
    # ---- 2026-10-17 逐道具/动作声响预览（docs §16.3 验收 2/3）----
    # 悬停/瞄准/物品详情的发声点与半径：口径由 core.sound_preview 提供。
    "回声脉冲（构想）声响半径：{n}": "Echo pulse (conception) noise radius: {n}",
    "发声点：你所在格 · 声响半径 {n}": "Sound origin: your cell · noise radius {n}",
    "发声点：落点 · 基础半径 {n}（按落点环境修正）":
        "Sound origin: landing cell · base radius {n} (modified by the landing environment)",
    "发声点：命中处 · 基础半径 {n}（按命中格环境修正）":
        "Sound origin: impact cell · base radius {n} (modified by the impact environment)",
    "落地({x},{y})：{effect}": "Landing ({x},{y}): {effect}",
    "落地不发声": "No sound on landing",
    "路径未完全可见，实际落点可能提前": "Path partly unseen; the throw may land early",
    "落地声响半径 {n}": "Landing noise radius {n}",
    "命中处声响半径 {n}": "Impact noise radius {n}",
    # 投掷落点效果类别（只有蜂鸣诱饵的「响声」会在落点发声）。
    "爆炸": "Explosion",
    "火星": "Sparks",
    "浓烟": "Thick smoke",
    "响声": "Noise",
    "普通落地": "Plain landing",
    # 预览 dict 的 note_key（发声入口标识；界面不一定直接渲染，补齐便于排查）。
    "踩踏声响": "Footstep noise",
    "回声脉冲（构想）": "Echo pulse (conception)",
    "投掷落点": "Throw landing",
    "汽笛长鸣": "Whistle blast",
    "发射载荷响声": "Ammo payload noise",
    "物品使用": "Item use",
    "蜂鸣诱饵落地": "Buzz lure landing",
    "装备载荷命中": "Equipment payload impact",
}


EN_MESSAGES: dict[str, str] = {
    # ---- 2026-10-15 补全：键位迁移提示 + 委托放弃（并行会话新增运行时消息）。
    "旧按键与现有操作冲突，已恢复可用键位。":
        "The old key conflicted with an existing action; a usable key has been restored.",
    "这项委托已失效，不能放弃。": "This task is no longer valid and cannot be abandoned.",
    "已放弃委托；腾出一个委托名额，不领取报酬。":
        "Task abandoned; a task slot is freed and no reward is paid.",
    "这一单已经放弃，不能交付。": "This task was abandoned and cannot be delivered.",
    '这个身份没有此项能力。': 'This identity does not have that ability.',
    '身份能力仍在冷却。': 'The identity ability is still cooling down.',
    '相邻没有可以退稿的墙。': 'There is no adjacent wall you can retract.',
    '这面墙不属于你的可撤回构想。': 'This wall is not one of your retractable constructs.',
    '你撤去了自己写下的墙。': 'You retract the wall you wrote into the dream.',
    '你在脚下留下了一小团雾。': 'You leave a small cloud of mist at your feet.',
    # ---- 拾取 / 行囊 ----
    "聚合弹数量必须为正数。": "Projectile count must be positive.",
    "获得 {amount} 枚聚合弹。": "Gained {amount} aggregate projectile(s).",
    "脚下没有可拾取的显化物。": "Nothing to pick up underfoot.",
    "记忆碎片已收纳：{item}。": "Memory fragment stored: {item}.",
    "替换了 {name}。": "Replaced {name}.",
    "背包已满，无法拾取这个显化物。": "Bag full — cannot pick up this manifestation.",
    '捡起所选': 'Take selected',
    '图像暂时不可用，已恢复字符地图；F2 可重试图像。':
        'Images are temporarily unavailable; the character map is active. Press F2 to retry images.',
    '另有 {n} 处同类在视野里没被点名（走近或悬停可换目标）':
        '{n} more of this kind are visible but unnamed here (move closer or hover to change target)',
    "拾取显化物：{item}。": "Picked up manifestation: {item}.",
    # ---- 面板点击兜底（左键按在没法结算的行上，必须给话而不是静默） ----
    "这一行现在没有可执行的操作。": "Nothing on this row can be acted on right now.",
    # ---- 异常地点 ----
    "附近没有可以回应的异常地点。": "No anomaly site nearby to respond to.",
    "意识行囊已满，异常地点暂时无法交付显化物。":
        "Mind inventory full — the site cannot hand over its manifestation yet.",
    "记忆槽替换了 {name}。": "Memory slot replaced {name}.",
    "缓冲生效：{name}。": "Buffered: {name}.",
    "你把声音投到 ({x}, {y})：那边响了一声。": "You throw a sound to ({x}, {y}): it rings there once.",
    "相邻没有可以敲的墙。": "No wall next to you can be knocked on.",
    "你在 ({x}, {y}) 的墙上敲出节拍：接下来 {n} 回合每回合一响，墙碎即止。": "You knock a beat on the wall at ({x}, {y}): one pulse per turn for {n} turns, ending if the wall breaks.",
    "{item}的敲击点已经不在了，节拍停了。": "The spot {item} was knocking is no longer there; the beat stops.",
    "上一次诱引已经过期，或不在本层。": "The last lure has expired, or is not on this layer.",
    "返场把 ({x}, {y}) 的那声诱引又放了一遍。": "Curtain call replays that lure at ({x}, {y}).",
    "身边没有被真实照亮的格。": "Nothing around you is genuinely lit.",
    "留影把当前光照区的 {n} 格地形轮廓记进了记忆。": "Afterimage records {n} tiles of terrain outline from the lit area.",
    "那一格上没有你自己的构想场。": "No conception field of yours covers that tile.",
    "那一格没有正在亮着的灯。": "Nothing on that tile is lit right now.",
    "这盏灯已经被裁过——同一次不叠加。": "That lamp is already narrowed — this does not stack.",
    "那一格放不下光——墙里没有照出去的路。": "Light cannot be placed there — a wall leaves nowhere to shine.",
    "那一格本来就有光，换过去会把原来的灯弄丢。":
        "That tile is already lit; moving the light there would lose the lamp it has.",
    "你没有自己布下的临时光源可搬。": "You have no temporary light of your own to move.",
    "光本来就在那一格。": "The light is already on that tile.",
    "你挡住 ({x}, {y}) 的灯，把它收成朝自己这一侧的扇区，{n} 回合内照不到别处。":
        "You shade the lamp at ({x}, {y}) into a cone toward yourself: for {n} turns it lights nothing else.",
    "你把光从 ({ox}, {oy}) 搬到 ({x}, {y})：剩下的 {n} 回合照旧，没有续期。":
        "You move the light from ({ox}, {oy}) to ({x}, {y}): the remaining {n} turns carry over, with no renewal.",
    "你收回了 {name}：场不再继续生效，已投下的材料不返。": "You withdraw {name}: the field stops taking effect, and the material already spent is not returned.",
    "获得 {names}。": "Gained {names}.",
    "没有留下可携带的显化物。": "No carryable manifestation was left behind.",
    "回应异常地点：{event}。{insight}{reward}":
        "Responded to the anomaly site: {event}. {insight}{reward}",
    # ---- 携带意象 ----
    "无念黑渊吞掉了记忆，你想不起怎么穿戴它。":
        "The Abyss of No-Thought swallowed your memory — you can't recall how to put it on.",
    "无念黑渊吞掉了记忆，你想不起怎么脱下它。":
        "The Abyss of No-Thought swallowed your memory — you can't recall how to take it off.",
    "无念黑渊吞掉了记忆，你想不起这些东西的用法。":
        "The Abyss of No-Thought swallowed your memory — you can't recall how these are used.",
    "意识行囊中没有这个承载位。": "No such slot in your mind inventory.",
    "{item}不能作为携带意象。": "{item} cannot serve as a carried image.",
    "{item}并未穿戴在身上。": "{item} is not worn.",
    "{item}当前不能直接使用。": "{item} cannot be used directly right now.",
    "已将 {item} 放入{slot}。": "Placed {item} into {slot}.",
    " 原有意象被替换。": " The previous image was replaced.",
    "已将 {item} 从{slot}脱下。": "Removed {item} from {slot}.",
    "{hanger}被挂上了梦的墙壁。": "{hanger} was hung on the wall of the dream.",
    # ---- 摄入物 ----
    "糖衣之下是救济：心智恢复了 15 点。":
        "Under the sugar coat is relief: mind restored by 15.",
    "过期的是药效本身：心智 −8，清醒度 −3。":
        "What expired was the effect itself: mind −8, lucidity −3.",
    "薄荷的凉意渗进神志：接下来持续恢复清醒度。":
        "Mint's chill seeps into your mind: lucidity will keep regenerating.",
    "迟滞与麻痹被冲开了。": "Sluggishness and numbness are washed away.",
    # ---- 易逝物 / 交互道具 ----
    "火焰在脚下的记忆上亮起。": "Flame kindles on the memory underfoot.",
    "脚下的液态记忆不导电。": "The liquid memory underfoot does not conduct.",
    "这里没有足够的液态记忆或弥散印象可供点燃。":
        "Not enough liquid memory or diffuse impression here to ignite.",
    "相邻没有可以点燃的液态记忆或弥散印象。":
        "No adjacent liquid memory or diffuse impression to ignite.",
    "静电尘里的电压叠加进了导电液态记忆。":
        "The voltage in the static dust feeds into the conductive liquid memory.",
    "导电液态记忆传递了清醒创伤，影响 {count} 个失控意识。":
        "The conductive liquid memory passed lucidity trauma, affecting {count} stray consciousness(es).",
    "你踩上空心的台阶，落空的这一次行动让崩解松了扣。":
        "You stepped on a hollow step; the wasted action loosened dissolution's grip.",
    "相邻没有受损的坚实聚合物。": "No damaged solid aggregate adjacent.",
    "先把光标悬停在一个格子上，卷尺才有可测量的距离。":
        "Hover the cursor over a cell first — only then does the tape measure have a distance.",
    "卷尺读数：到悬停格最短 {steps} 步。":
        "Tape reading: shortest {steps} step(s) to the hovered cell.",
    "汽笛的长鸣在梦里扩散开来。": "The whistle's long blast spreads through the dream.",
    "白光淹没视野，{count} 个失控意识暂时看不清你。":
        "White light floods the view; {count} stray consciousness(es) temporarily lose sight of you.",
    "强光冲淡了视野：{count} 个失控意识的视距暂时减半。":
        "The flash thins the view: {count} stray consciousness(es) have their sight range halved for now.",
    "{count} 个意识不看眼睛，光对它们没有意义。":
        "{count} mind(s) do not look with eyes; light means nothing to them.",
    "脚下的格子变得比谎言还滑。": "The cell underfoot turns slicker than a lie.",
    "余热点燃了相邻的一格记忆。": "Residual heat ignites an adjacent cell of memory.",
    "有 {count} 个失控意识的动作被拖住了。":
        "{count} stray consciousness(es) are slowed down.",
    "相邻没有可以被弹簧推开的目标。": "No adjacent target to push with the spring.",
    "弹簧折叠件把 {target} 推了出去。": "The coiled spring shoves {target} away.",
    "镜面碎片架在了你和梦之间。": "The mirror shard stands between you and the dream.",
    "镜面碎片架在了你和梦之间（{turns} 回合内有效）。":
        "The mirror shard stands between you and the dream (good for {turns} rounds).",
    "镜面碎片架在你和梦之间：下一记打击会被退回（剩 {turns} 回合）。":
        "The mirror shard stands between you and the dream: the next blow is turned back ({turns} rounds left).",
    "镜面碎片的光褪了——它没能等到下一记打击。":
        "The mirror shard dims: it never met the blow it was waiting for.",
    "{item}又嗡了一声——声音还在原处。":
        "The {item} buzzes again — still from the same spot.",
    "底片上的两次成像叠在一起（{turns} 回合内下一个动作不耗时）。":
        "Two exposures sit on the same frame (the next action within {turns} rounds costs no time).",
    "底片上的第二次成像褪了——它没等到那个动作。":
        "The second exposure on the film has faded: it never met that action.",
    "三格内没有看得见、按得响的机关。":
        "No mechanism you can see within three cells answers a press.",
    "键帽在指下响了一声——{name}应声而动。":
        "The keycap clicks under your thumb — {name} answers.",
    "下一个正式动作不耗时（剩 {turns} 回合内有效）。":
        "The next proper action costs no time ({turns} rounds left to use it).",
    "{item}还剩 {n} 只要投——每次部署各花一次行动。":
        "{item}: {n} can left to throw — each deployment costs an action.",
    "焦油又淌开一层（{n} 单位燃油）。":
        "Another layer of tar spreads out ({n} units of fuel).",
    "{item}在脚下碎开，焦油一层层淌出来（点燃 {n} 格）。":
        "The {item} breaks open underfoot and the tar pours out in layers ({n} cells alight).",
    "{item}在远处碎开，焦油一层层淌出来（点燃 {n} 格）。":
        "The {item} breaks open in the distance and the tar pours out in layers ({n} cells alight).",
    "镜面已经架好了：再叠一片不会多挡一次。":
        "A mirror is already up; a second shard cannot block twice.",
    "铃声传到的地方，有 {count} 个失控意识慢了下来。":
        "Where the bell reaches, {count} unbound consciousness(es) slow down.",
    "{item}在脚下炸成一圈火星（点燃 {n} 格）。":
        "{item} bursts into a ring of sparks underfoot ({n} cell(s) lit).",
    "{item}在远处炸成一圈火星（点燃 {n} 格）。":
        "{item} bursts into a ring of sparks in the distance ({n} cell(s) lit).",
    "构想早已全部习得，书页化作 10 点想象力。":
        "All conceptions were long learned; the page becomes 10 imagination.",
    "你习得了主动构想「{name}」（{description}）":
        "You learned the active conception “{name}” ({description})",
    "{item}的效果尚未稳定。": "{item}'s effect has not settled yet.",
    "使用了 {item}。": "Used {item}.",
    # ---- 主动构想 ----
    "未知的构想。": "Unknown conception.",
    "{name}仍在冷却（剩 {turns} 回合）。":
        "{name} is still cooling down ({turns} rounds left).",
    "主动构想「{name}」展开了。": "The active conception “{name}” unfolds.",
    "火花构想擦亮了相邻的记忆，火焰亮起。":
        "Spark conception kindles adjacent memory; flame rises.",
    "望远构想展开了：视野 +3，持续 5 回合。":
        "Farsight conception unfolds: vision +3 for 5 rounds.",
    "迟缓构想拖住了 {count} 个失控意识。":
        "Slow-wave conception drags down {count} stray consciousness(es).",
    "显影构想让 {count} 格地形永久显影。":
        "Develop conception permanently develops {count} cells of terrain.",
    "相邻没有可以推开的失控意识。": "No adjacent stray consciousness to push.",
    "推斥构想把 {count} 个失控意识推了出去。":
        "Repulse conception shoves {count} stray consciousness(es) away.",
    "镜面构想架起了看不见的镜子。": "Mirror conception raises an invisible mirror.",
    "视野内没有可以曝光的失控意识。":
        "No stray consciousness in sight to overexpose.",
    "曝光构想让 {count} 个失控意识过曝失明。":
        "Exposure conception blinds {count} stray consciousness(es).",
    "修缮了相邻的{wall}（完整度 {value}/{maximum}）。":
        "Repaired the adjacent {wall} (integrity {value}/{maximum}).",
    # ---- 投掷 / 放下 / 发射 ----
    "投掷方向无效。": "Invalid throw direction.",
    "投掷了 {item}。": "Threw {item}.",
    "放下了 {item}。": "Dropped {item}.",
    "携带意象仍在使用中，不能投掷。":
        "The carried image is still in use; it can't be thrown.",
    "携带意象仍在使用中，不能直接放下。":
        "The carried image is still in use; it can't be dropped directly.",
    "发射许可已经解锁。": "Fire clearance is already unlocked.",
    "想象力不足，无法解锁发射许可。":
        "Not enough imagination to unlock fire clearance.",
    "现实洞察展开：发射许可已解锁。":
        "Reality insight unfolds: fire clearance unlocked.",
    "尚未解锁发射许可，也没有可消耗的聚合弹。":
        "Fire clearance is not unlocked, and no aggregate projectiles are left to spend.",
    "发射方向无效。": "Invalid fire direction.",
    "弹体命中失控意识。": "The projectile hits a stray consciousness.",
    "弹体撞上坚实聚合物。": "The projectile strikes solid aggregate.",
    "弹体击碎了一处坚实聚合物。":
        "The projectile shatters a patch of solid aggregate.",
    "弹体飞出有效距离后消散。":
        "The projectile dissipates after flying its effective range.",
    "弹体消失在梦境结构中。": "The projectile vanishes into the dream's structure.",
    # ---- 移动 / 撞墙 ----
    "一次只能移动一格。": "You can only move one cell at a time.",
    "边界阻挡了你。": "The boundary blocks you.",
    "你移动了一格。": "You moved one cell.",
    "你对 {target} 造成一次接触创伤。":
        "You dealt a contact trauma to {target}.",
    "放大的身体挤不过这扇门。": "Your enlarged body can't squeeze through this door.",
    "放大的身体挤过缝隙，多花了些时间。":
        "Your enlarged body squeezes through the gap, costing extra time.",
    "这一步没有花掉任何时间。": "This step cost no time.",
    "粘稠的梦拖住了你的脚步。": "The viscous dream drags at your steps.",
    "你沾染了「{name}」的征兆。": "You caught the “{name}” omen.",
    "一件家具在你面前展开了轮廓——是人形衣架！":
        "A piece of furniture unfolds before you — a human coat rack!",
    "只能打开相邻的坚实聚合物。": "You can only open adjacent solid aggregate.",
    "这里没有可以打开的坚实聚合物。": "No solid aggregate here to open.",
    "门开了，你跨了进去。": "The door opens; you step through.",
    "徒手无法破坏这种坚实聚合物。":
        "This kind of solid aggregate can't be broken bare-handed.",
    "{wall}松动了（完整度 {value}/{maximum}），再推几次就能推倒。":
        "The {wall} loosened (integrity {value}/{maximum}); a few more pushes will topple it.",
    "{wall}被你徒手推倒了。": "You pushed the {wall} over bare-handed.",
    "封存的东西淌了一地。": "Its sealed contents spill everywhere.",
    "你捧起生米吃了下去，清醒度 +3，随后困意袭来。":
        "You scoop up the raw rice and eat it: lucidity +3, then drowsiness.",
    "这里没有植物可拔。": "No plant here to pull up.",
    "你把脚下的植物连根拔起了。": "You uproot the plant underfoot.",
    # 稀有植物拔除收益（2026-09-18）：收益写在植物定义里，这三条是拼句子用的。
    "{plant}：{rewards}。": "{plant}: {rewards}.",
    "沾染「{name}」": "Take on \"{name}\"",
    "获得 {item}": "Gain {item}",
    "散出少量{name}": "A little {name} spills out",
    "你等待了一个行动。": "You waited one action.",
    "脚下的水银微微蒸腾：本格气体的触发浓度 −5（至少 1）。":
        "Mercury underfoot gently fumes: this cell's gas threshold −5 (minimum 1).",
    # ---- 异象 ----
    "{enemy}把这一下反了回来，造成{harm}。":
        "{enemy} turned that blow back, dealing {harm}.",
    "本体崩解，它的残影随之褪成空白。":
        "The main body dissolves; its afterimage fades to blank.",
    "{enemy}的台阶缝隙里落下了一撮阁楼的灰尘。":
        "A pinch of attic dust falls from {enemy}'s step gap.",
    "失序档 {tier} 使 {enemy} 多留下了一枚脱落的键帽。":
        "Disorder tier {tier} made {enemy} leave behind a fallen keycap.",
    "{enemy}崩解，留下了 {item}。": "{enemy} dissolves, leaving {item}.",
    "声波脉冲扫过，{count} 个失控意识听见了声源。":
        "The sound pulse sweeps past; {count} stray consciousness(es) hear the source.",
    "{count} 个失控意识起了疑心，正在靠近声源。":
        "{count} stray consciousness(es) grow suspicious and close in on the source.",
    "无声步 −1": "Silent Step −1",
    "无声步/足音消音 −2": "Silent Step / Muted Footfalls −2",
    "身处回声雾 ×2": "inside echo fog ×2",
    "紧邻尖啸瓷墙 ×2": "adjacent shrieking porcelain ×2",
    "静默协议 →1": "Silence Protocol →1",
    "回声 ×{multiplier}": "Echo ×{multiplier}",
    "沉思铁幕 →0": "Iron Curtain →0",
    "{name} −{reduction}": "{name} −{reduction}",
    "声响: 近战 {melee} · 投掷 {throw}": "Noise: melee {melee} · throw {throw}",
    "↳ {source}": "↳ {source}",
    "眼前没有可以改写的名字。":
        "Nothing within sight carries a name you can rewrite.",
    "视野里没有可以改写的名字。":
        "Nothing visible carries a name you can rewrite.",
    "这个字词用不到这个名字上。": "That word does not apply to this name.",
    "地图上的字句": "Words on the map",
    "  想象力 {a} · 混乱 +{b}": "  Imagination {a} · Chaos +{b}",
    "效果：{note}": "Effect: {note}",
    "效果：—": "Effect: —",
    "←→ 换名字 · ↑↓ 换字词 · Enter 执行 · Esc 返回":
        "←→ switch name · ↑↓ switch word · Enter cast · Esc back",
    "↑↓ 选字词 · Enter 进确认 · Esc 退出":
        "↑↓ pick a word · Enter to confirm · Esc exit",
    "它已经在追你了。": "It is already chasing you.",
    "稳定意识不吃这一套。": "A stable mind does not fall for this.",
    "这段文字太深，删不动。": "This text runs too deep to erase.",
    "这一层的删除额度用完了（{n} 次）。":
        "This layer's deletion quota is used up ({n} times).",
    "没有这个名字。": "There is no such name.",
    "（想象力 −{n}，混乱度 {chaos}／{tier}）":
        "(Imagination −{n}, Chaos {chaos}/{tier})",
    "你的呼唤被 {enemy} 听见了。": "Your call was heard by {enemy}.",
    "{enemy}循声向你走来。": "{enemy} walks toward you, following the sound.",
    "它没有理会这段文字。": "It pays this text no mind.",
    "{enemy}被这段文字惊散了。": "{enemy} is startled apart by this text.",
    "{enemy}转身离开，一时不会再主动找你。":
        "{enemy} turns away and will not hunt you for a while.",
    "你把「{name}」从眼前抹去了。": "You erase \"{name}\" from sight.",
    "这个字词还没有学会。": "You have not learned this word yet.",
    "你把「{name}」磨进了尘埃。": "You grind \"{name}\" into dust.",
    "「{name}」被损坏了。": "\"{name}\" is damaged.",
    "流动的东西写不住「破坏」。": "Flowing things cannot hold the word \"break\".",
    "这里没有可以损坏的东西。": "There is nothing here to damage.",
    "这段文字太深，改不动。": "This text runs too deep to alter.",
    "「{name}」塌了。": "\"{name}\" collapses.",
    "「{name}」出现了裂痕。": "Cracks spread across \"{name}\".",
    "「{name}」从地图上消失了。": "\"{name}\" vanishes from the map.",
    "「{name}」被抹干了。": "\"{name}\" is wiped dry.",
    "「{name}」被抹散了。": "\"{name}\" is dispersed.",
    "「{name}」被收走了。": "\"{name}\" is taken away.",
    "这里没有可以删除的东西。": "There is nothing here to delete.",
    "自我察觉": "Self-Awareness",
    "属性": "Attributes",
    "征兆": "Portents",
    "此刻没有附着任何征兆。": "No portents cling to you right now.",
    "此刻用不上它。": "It has no use right now.",
    "清醒创伤减免": "Lucidity trauma reduction",
    "心智创伤减免": "Mind trauma reduction",
    "爆炸 +{explosion} · 火焰蔓延 +{fire} · 崩解收益 {dissolution} · 气体消散 +{gas} 回合":
        "Explosion +{explosion} · Fire spread +{fire} · Dissolution {dissolution} · Gas lingers +{gas} turns",
    "当前 {value}/{maximum}": "Current {value}/{maximum}",
    "爆炸增强": "Explosion boost",
    "火焰蔓延": "Fire spread",
    "穿透加成": "Penetration bonus",
    "坚固度惩罚": "Solidity penalty",
    "崩解收益": "Dissolution gain",
    "战利品幸度": "Loot luck",
    "想象上限": "Imagination cap",
    "标准": "Standard",
    "近战创伤": "Melee trauma",
    "远程创伤": "Ranged trauma",
    "移动速度": "Move speed",
    "攻击速度": "Attack speed",
    "2（投掷）/ 随发射物": "2 (throw) / per projectile",
    "2（投掷）": "2 (throw)",
    "篡改 · 地图观察": "Tamper · Map preview",
    "[返回编辑 V]": "[Back to editor V]",
    "[查看地图 V]": "[View map V]",
    "[取消篡改]": "[Cancel tamper]",
    "目标：{name}": "Target: {name}",
    "观察格：({x},{y})": "Observed cell: ({x},{y})",
    "编辑不推进回合；V 查看地图。": "Editing does not advance turns; V opens the map preview.",
    "1 回合/格": "1 turn/tile",
    "1 回合/次": "1 turn/hit",
    "1 回合/次（亚回合武器更快）": "1 turn/hit (sub-turn weapons are faster)",
    # 自我觉察真实展示（2026-10-18 docs §10 第一批：基础值与条件分开）
    "近战·基础创伤": "Melee · base trauma",
    "近战·基础耗时": "Melee · base time",
    "近战·有效耗时": "Melee · effective time",
    "移动·基础耗时": "Move · base time",
    "移动·有效耗时": "Move · effective time",
    "移动·迟滞代价": "Move · delay burden",
    "攻击·迟滞代价": "Attack · delay burden",
    "行动速度倍率": "Action speed multiplier",
    "{n:g} 回合/次": "{n:g} turn/hit",
    "{n:.2f} 回合/次": "{n:.2f} turn/hit",
    "{n:.2f} 回合/格": "{n:.2f} turn/tile",
    "+{n:g}（积满 1 多花 1 回合）": "+{n:g} (each full point costs one extra turn)",
    "×{n:g}": "×{n:g}",
    "+{n}": "+{n}",
    "−{n}": "−{n}",
    "+{n}%": "+{n}%",
    "{n:+.1f}": "{n:+.1f}",
    "投掷·距离": "Throw · range",
    "投掷·威力": "Throw · power",
    "按所用物品（爆炸/火焰/落地）": "By the thrown item (blast/fire/landing)",
    "{n} 格": "{n} tiles",
    "{n}%（战斗韧性，未含护甲与缓冲）":
        "{n}% (combat resilience; armor and one-time buffers excluded)",
    "摇篮曲在你耳边打转：想象力自然回流暂停。":
        "A lullaby circles your ears: natural imagination recovery is paused.",
    "每回合自然回流约 {rate:g} 点（含医院恢复率与开局修正）。":
        "Natural recovery about {rate:g} per turn (hospital rate and run options included).",
    "留白线见底时再补 {n} 点。": "Blank-edge lines add {n} more when empty.",
    "此刻见底：构想与改写暂时不可用，自然回流仍会把你一点点填回来。":
        "Currently empty: abilities and rewrites are unavailable, but natural recovery still refills you.",
    "当前 {value}/{maximum} · 下一回合进度 {credit:.2f}":
        "Now {value}/{maximum} · next-turn progress {credit:.2f}",
    "状态读取失败。": "Failed to read your state.",
    "视线清亮，地图四角没有暗影。穿墙与碰撞都还按梦的规矩来。":
        "Your sight is clear and the map corners hold no shadow. Walls and impacts still obey the dream's rules.",
    "视野边缘浮起一圈暗影。穿墙的构想开始多走一寸，坚固的东西也不再那么可靠。":
        "A ring of shadow rises at the edge of sight. Wall-passing ideas reach a little further, and solid things stop being dependable.",
    "暗影压得更近，画面蒙上一层细噪。你的爆炸与构想更容易穿透阻隔，也更容易把家具震散。":
        "Shadows crowd closer and a fine noise films the screen. Your blasts and ideas pierce barriers more easily — and shake furniture apart more easily too.",
    "清醒见了底——每几次呼吸就要磨损一点心智，穿墙与震散都到了极限。":
        "Lucidity is spent — every few breaths wear at your mind, and wall-passing and shattering are at their limit.",
    "穿透加成 +{penetration} · 坚固度惩罚 −{solidity} · 心智侵蚀 {drain}":
        "Penetration +{penetration} · Solidity penalty −{solidity} · Mind erosion {drain}",
    "每 5 回合 −1": "−1 per 5 turns",
    "无": "none",
    "思绪清明。异象的名字都还认得出来，爆炸也只烧该烧的地方。":
        "Your thoughts are clear. You still recognize every anomaly's name, and explosions burn only what they should.",
    "有些东西开始说不准——偶尔会觉得眼前的轮廓「像是」别的什么。爆裂比平时更容易脱缰。":
        "Some things stop adding up — now and then a silhouette looks \"like\" something else. Blasts slip their leash more easily.",
    "视野里的轮廓融成一团团未定形的东西，地图边缘也在发暗。你的爆炸与火焰明显更野，梦给的战利品也更多。":
        "Shapes melt into unformed blobs and the map's edges darken. Your explosions and fires run wilder, and the dream pays out more.",
    "心智见底。每几次呼吸就要被抽走一点清醒，梦彻底脱了缰。":
        "Your mind is spent. Every few breaths cost you lucidity, and the dream has slipped its reins entirely.",
    "念想尚有余额——构想与改写都从这里扣。它不会自然回来，用一点少一点。":
        "Imagination still has a balance — every conceiving and rewriting is paid from here. It never comes back on its own.",
    "念想见底了。此刻任何构想与改写都无从落笔，得先想办法找回一点念想。":
        "Imagination is spent. Nothing can be conceived or rewritten right now — find a way to recover some first.",
    "近战它会听见你（声响半径 {n}）": "A melee strike will be heard (noise radius {n})",
    "踩踏会发声（半径 {n}）": "Stepping here makes noise (radius {n})",
    "镜面碎片把 {enemy} 的打击原路退了回去。":
        "The mirror shard sends {enemy}'s blow back the way it came.",
    "打击落在了挂着的{hung}上，替你挡下了这次创伤。":
        "The blow lands on the hung {hung}, taking this trauma for you.",
    "{enemy}剪走了你的{stolen}，它掉在了你的脚下。":
        "{enemy} snipped away your {stolen}; it drops at your feet.",
    "{enemy}造成了{trauma}。": "{enemy} dealt {trauma}.",
    "{enemy}失去了你的踪迹。": "{enemy} lost your trail.",
    "底片上的第二层显影走了出来。":
        "The second exposure on the negative steps out.",
    "空心的灯塔发动「照彻」：全图被照亮 2 回合，所有异象都看见了你的位置。":
        "The hollow lighthouse triggers “Illumination”: the map is lit for 2 rounds and every anomaly sees your position.",
    "迁徙的楼梯碾压而过，你被推开了 1 格并受到清醒创伤。":
        "The migrating staircase grinds past: you are shoved 1 cell and take lucidity trauma.",
    "你被楼梯死死压在墙上。": "The staircase pins you hard against the wall.",
    "一段楼梯在梦里缓缓迁徙。": "A staircase slowly migrates through the dream.",
    "远处的结构里又生成了一只纸页犬。":
        "Another page hound forms in the distant structure.",
    # ---- 时间 / 终局 ----
    "底片上的第二次成像先于时间完成。":
        "The second exposure on the negative finishes before time does.",
    "{sources}让你多沉了 {extra} 回合。": "{sources} made you sink {extra} more round(s).",
    "时间被偷走了一格，这一回合提前结束。":
        "A notch of time was stolen; this round ends early.",
    "意识沉没。": "Consciousness sinks.",
    # ---- 材料反应 ----
    "显影液淌过 {count} 格，它们的地形留在了视野里。":
        "Developer fluid ran over {count} cells; their terrain stays in view.",
    "冲击折页爆发，影响 {count} 个失控意识。":
        "The impact fold bursts, affecting {count} stray consciousness(es).",
    "清醒度归零，远域覆写永久改变了 {count} 个格子。":
        "Lucidity hit zero; far-field overwrite permanently changed {count} cells.",
    "碎瓷划过你，清醒度 −1。": "Shards of porcelain graze you: lucidity −1.",
    "碎瓷擦身而过，灰烬记忆把余烬换成了 3 点想象力。":
        "The shards pass you by; ash memory turns the embers into 3 imagination.",
    "梦晶簇碎裂，储存的气体尽数涌出。":
        "The dream crystal cluster shatters, releasing all its stored gas.",
    "超临界流体渗进墙体缝隙，石体簌簌剥落。":
        "Supercritical fluid seeps into the wall's cracks, and stone flakes away.",
    "盐晶壁遇水，簌地溶掉了。": "The salt crystal wall meets water and dissolves at once.",
    "蜡化记忆墙在火焰旁缓缓融尽了。":
        "The waxed memory wall slowly melts away beside the flame.",
    "烛泪柱燃尽了，蜡泪淌了一地。":
        "The candle tear pillar burns out, wax running everywhere.",
    "枕木在火里化进了安眠香。": "The sleepers melt into sleep incense in the fire.",
    "黄粱米堆烧成了催眠的青烟。":
        "The millet mound burns into hypnotic smoke.",
    # ---- 材料反应配方播报（2026-09-18，materials/reactions.py）----
    "酒气渗进水面，清水悄悄酿成了红酒。":
        "Alcohol vapor seeps into the water, quietly brewing it into red wine.",
    "液氮吞下水汽，凝出一缕晨霜清气。":
        "Liquid nitrogen swallows the vapor, condensing into a wisp of morning frost.",
    "蜂蜜粘住了灰尘云，搅成一摊蜜灰膏。":
        "Honey catches the dust cloud and churns into honey-ash paste.",
    "静电尘落进导电液，液面腾起一层电浆雾。":
        "Static dust falls into the conductive liquid; a layer of plasma mist rises.",
    "熔念金属淬进灼热蒸汽，呛出一股黑烟。":
        "Molten thought-metal quenches in scalding steam, coughing out black smoke.",
    "水汽漫过显影液，药性被冲淡成稀释记忆。":
        "Vapor washes over the developer, diluting it into diluted memory.",
    "熔蜡遇冷凝固，立起一堵蜡化记忆墙。":
        "Molten wax freezes in the cold, rising as a waxed memory wall.",
    "水面霎时结冰，冻成一片打滑的冰面。":
        "The water surface freezes at once into a slippery sheet of ice.",
    "液面霎时结冰，冻成一片打滑的冰面。":
        "The liquid surface freezes at once into a slippery sheet of ice.",
    "熔念金属渗进墙体，石体被烫得熔穿。":
        "Molten thought-metal seeps into the wall, melting straight through the stone.",
    "酸蚀液泼上盐晶壁，墙体崩解、呛出一蓬毒气。":
        "Acid splashes onto the salt crystal wall; it crumbles, belching poison gas.",
    "烛泪柱被冻得脆裂开来。":
        "The candle tear pillar freezes brittle and shatters.",
    # ---- 征兆 ----
    "水把身上的「{name}」冲净了。": "Water washed the “{name}” off you.",
    "「{name}」的征兆散去了。": "The “{name}” omen has faded.",
    "静电尘把你身上的残余电流续上了：清醒度又掉了一点。":
        "The static dust renews the residual current in you: lucidity drops again.",
    "身上的可燃气体被引燃了：清醒度 −1。":
        "The flammable gas on you ignites: lucidity −1.",
    "蜂蜜裹住伤口，清醒度回暖了一分。":
        "Honey coats the wound; lucidity warms back by one.",
    "泪滴溶液让你的心智回暖了一分。":
        "The tear solution warms your mind back by one.",
    "发飘的手拖慢了这次出手。": "A floating hand slowed this strike.",
    "浓缩咖啡因的账单到了：清醒度 −1。":
        "The espresso bill arrives: lucidity −1.",
    "灯塔的光收了回去，梦境重新合拢。":
        "The lighthouse's beam withdraws; the dream closes again.",
    "核心执念停止书写。你找到了醒来的条件。":
        "The core obsession stops writing. You have found the condition to wake.",
    # ---- 下潜 ----
    "崩解度已达 100：可以下潜了（按 N）。":
        "Dissolution reached 100 — you can descend (press N).",
    "崩解度还不足以下潜（当前 {value}/100）。":
        "Dissolution is not enough to descend (currently {value}/100).",
    "没有可回溯的更浅梦层。": "No shallower layer to backtrack to.",
    "清醒度不足，强行下潜并承受 {amount} 点心智创伤。":
        "Not enough lucidity — you force the descent and take {amount} mind trauma.",
    "下潜至梦层 {depth}。": "Descended to dream layer {depth}.",
    "回溯至梦层 {depth}。": "Backtracked to dream layer {depth}.",
    "入梦结束。已形成的记忆碎片可以留给下一局。":
        "The descent is over. The memory fragments you formed can be kept for the next run.",
    "只有意识沉没或完成第六层牵引后才能结束入梦。":
        "You can only end the descent after consciousness sinks or the layer-six pull is complete.",
    "这次入梦已经结束。": "This descent is already over.",
    "获得现实洞察：{name}。": "Gained reality insight: {name}.",
    "现实洞察 {name} 取代了 {replaced}。":
        "Reality insight {name} replaced {replaced}.",
    "现实洞察已满：{name} 无处安放，需要替换或放弃。":
        "Reality insights are full: {name} has nowhere to settle — replace or discard it.",
    "放弃了现实洞察 {name}。": "Discarded the reality insight {name}.",
    "现实洞察已满": "Reality insights are full",
    "获得：": "Gained: ",
    "选择一条替换，或按 Esc 放弃这条新洞察：":
        "Pick one to replace, or press Esc to discard this new insight:",
    "确定放弃替换吗？": "Give up the replacement?",
    "Enter / Y = 放弃这次洞察　　其它键 = 返回":
        "Enter / Y = discard this insight    any other key = back",
    "↑↓ 选择 · Enter 替换 · Esc/Q 放弃":
        "↑↓ select · Enter replace · Esc/Q discard",
    # ---- 记忆碎片（第一批实装）----
    "记忆碎片已满": "Memory fragments are full",
    "选择一片替换，或按 Esc 放弃这片新碎片：":
        "Pick one to replace, or press Esc to discard this new fragment:",
    "Enter / Y = 放弃这片碎片　　其它键 = 返回":
        "Enter / Y = discard this fragment    any other key = back",
    "记忆碎片 {name} 取代了 {replaced}。":
        "Memory fragment {name} replaced {replaced}.",
    "放弃了记忆碎片 {name}。": "Discarded the memory fragment {name}.",
    "记忆碎片已满：{name} 无处安放，需要替换或放弃。":
        "Memory fragments are full: {name} has nowhere to settle — replace or discard it.",
    "记忆碎片已满：{item} 无处安放，需要替换或放弃。":
        "Memory fragments are full: {item} has nowhere to settle — replace or discard it.",
    "记忆槽：": "Memory slots: ",
    "火花构想擦亮了——相邻没有可燃的记忆，火苗空落在地。":
        "The spark flares — no flammable memory is adjacent, and the flame falls on empty ground.",
    "推斥构想推开了空气——相邻没有可以被推开的失控意识。":
        "The repulsion pushes only air — no stray consciousness is adjacent.",
    "曝光构想亮了亮——视野内没有可以曝光的失控意识。":
        "The exposure flashes — no stray consciousness is in sight.",
    # ---- 生成 / 存档 ----
    "上一局的记忆碎片仍在：{item}。":
        "Memory fragments from the last run remain: {item}.",
    "进入梦层 {depth}。崩解度 0/100。":
        "Entered dream layer {depth}. Dissolution 0/100.",
    "存档槽必须在 1 到 3 之间。": "The save slot must be between 1 and 3.",
    "没有可恢复的梦痕。": "No recoverable dream trace.",
    "未知命令：{command}": "Unknown command: {command}",
    "视野内存在失控意识，自动收纳暂停。":
        "A stray consciousness is in sight — auto pickup paused.",
    "这次入梦已经结束，不能继续行动。":
        "This descent is over; you cannot act any further.",
    # ---- 运行中消息补全（六项改动后的新增/对齐） ----
    "灵视的代价：又有 {count} 个失控意识看见了你的位置。":
        "The price of true sight: {count} more stray consciousness(es) now see your position.",
    "沉眠": "Deep Sleep",
    # docs §19 E：旧消息日志保留写入时的语言，读档后需说明这一限制。
    "较早的记录保留当时的语言，不随当前语言重译。":
        "Older log entries keep the language they were written in; they are not retranslated.",
    # 顿号/量词：中文用「、」连接并列项，英文换成逗号。
    "、": ", ",
    # 全角括号/全角空格：中文排版用全角，英文换成半角（行囊记忆槽摘要等）。
    "（": " (",
    "）": ")",
    "｜": ": ",
    "　": " ",
    "  {kinds} 种 · {total} 个": "  {kinds} kinds · {total} total",
}


EN_PLACES: dict[str, str] = {
    # ---- 层型（状态栏显示） ----
    "整齐的房间": "Tidy Rooms",
    "破碎的房间": "Shattered Rooms",
    "居民区": "Residential District",
    "洞穴": "Caverns",
    "迷宫": "Labyrinth",
    "长廊": "Long Gallery",
    "无限房间": "Endless Rooms",
    "碎影平原": "Shardshadow Plains",
    "回声大厅": "Echo Hall",
    "大厅": "Hall",
    "传统房间群": "Classic Room Cluster",
    "障碍平原": "Obstacle Plains",
    # ---- 楼层修饰符（状态栏显示） ----
    "气密": "Airtight",
    "潮湿": "Damp",
    "繁茂": "Lush",
    "古朴": "Antique",
    "大型": "Large",
    "小型": "Small",
    # ---- vault 模板名（开发用，未直接展示） ----
    "中央大厅": "Great Hall",
    "十字圣所": "Cross Sanctuary",
    "双子庭院": "Twin Courtyard",
    "环形回廊": "Ring Cloister",
    "辐射枢纽": "Radiation Hub",
    "长图书馆": "Long Library",
    "阶梯剧场": "Tiered Theatre",
    "四叶庭": "Four-leaf Court",
    "密室": "Hidden Chamber",
    "尽头书房": "Study at the End",
    "断桥": "Broken Bridge",
    "柱亭": "Column Pavilion",
    "祭坛": "Altar",
    "迷你迷宫": "Mini Labyrinth",
    "半隔断": "Half Partition",
    "双凳": "Twin Stools",
    "矮凳": "Low Stool",
    "矮墙段": "Low Wall Stub",
    "角垛": "Corner Buttress",
    "角柜": "Corner Cabinet",
    "共鸣台": "Resonance Dais",
    "回音壁": "Echo Wall",
    "壁龛": "Niche",
    "小天井": "Small Atrium",
    "巨石环": "Megalith Ring",
    "拱门排": "Arcade Row",
    "晾衣巷": "Clothesline Alley",
    "柱廊": "Colonnade",
    "柱阵": "Pillar Array",
    "独石": "Monolith",
    "石笋簇": "Stalagmite Cluster",
    "蘑菇环": "Mushroom Ring",
    "钟乳柱": "Stalactite Column",
    # ---- 生成期报错（开发用） ----
    "未知层型：": "Unknown map form: ",
    "地图至少需要 7x7 格": "The map needs at least 7x7 cells",
    "墙体厚度上限必须至少为 1 格": "The wall thickness cap must be at least 1 cell",
    "地势网格尺寸必须至少为 2": "The elevation grid must be at least 2",
    "梦层深度必须在 1 到 20 之间": "Dream layer depth must be between 1 and 20",
    # ---- 图鉴：材料三类（聚合物 / 液态记忆 / 弥散印象） ----
    "聚合物": "Polymers",
    "种类": "Type",
    "地面": "Floor",
    "墙": "Wall",
    "硬度": "Hardness",
    "厚度": "Thickness",
    "贴近效果": "Proximity",
    "特性": "Traits",
    "封存内容物": "seals contents",
    "可直接穿行": "can be walked through",
    "流动速度": "Flow",
    "黏度": "Viscosity",
    "接触效果": "Contact",
    "触发浓度": "Trigger",
    "易燃": "Flammable",
    "扩散速度": "Diffusion",
    "消散速度": "Dissipation",
    "遮蔽强度": "Obscurity",
    "吸入效果": "Inhalation",
    # ---- 格子详情：地势行与地面高低说明 ----
    "地势": "Elevation",
    "地势是本格在全层的高度（0 低洼 – 3 高处）：液体按地势差流向低处，低洼处更容易积液。聚合地面之间的高低只是观感差异，不影响行走；各变体另有一点点不造成伤害的小效果。": (
        "Elevation is this cell's height across the layer (0 = lowland, 3 = high ground): liquid flows downhill "
        "with the terrain, and lowlands pool more easily. The height difference between polymer floors is only a "
        "look and never affects walking; each variant carries one small, harmless effect of its own."
    ),
    # ---- 设置：删除历史统计（两段确认的危险动作） ----
    "删除历史统计": "Delete history stats",
    "清除图鉴里的遭遇/解决/交互等历史记录，不可恢复。": (
        "Clears encounter/resolution/interaction history in the catalog. This cannot be undone."
    ),
    "点击删除": "Click to delete",
    "再次点击确认删除": "Click again to confirm",
    "将删除全部历史统计且不可恢复；再次点击确认。": (
        "This deletes ALL history stats and cannot be undone; click again to confirm."
    ),
    "历史统计已删除。": "History stats deleted.",
    "此项需要按 Enter 确认。": "This option must be confirmed with Enter.",
    "当前没有可执行的删除操作。": "There is no delete action to run.",
    # ---- 设置：一键解锁全部图鉴 ----
    "一键解锁全部图鉴": "Unlock the whole codex",
    "把图鉴中所有条目标记为已解锁，便于查阅资料。": (
        "Marks every codex entry as unlocked, for easy reference."
    ),
    "点击解锁": "Click to unlock",
    "图鉴已全部解锁（新标记 {n} 条）。": "Codex fully unlocked ({n} newly marked).",
    "当前没有可执行的解锁操作。": "There is no unlock action to run.",

    # ---- 面板光标锁定（~） ----
    "锁定": "Lock",
    "~ 光标锁定：↑↓ 滚动面板 · ←→ 切页 · Enter 激活 · 点击地图或 ~ 解锁": (
        "~ Cursor lock: ↑↓ scroll panel · ←→ switch page · Enter activate · click map or ~ to unlock"
    ),

    # ---- 台子取物 ----
    "只能从相邻的台子上取物。": "You can only take items from an adjacent platform.",
    "这里没有台子。": "There is no platform here.",
    "台面上没有东西。": "Nothing is on the platform.",
    "从台面上取走：{item}。": "Taken from the platform: {item}.",
    "拾取携带意象：{item}。": "Picked up a carried image: {item}.",
    "从台面上取走携带意象：{item}。": "Taken from the platform (carried image): {item}.",
    # ---- 台面放置（§14.6） ----
    "放到台面": "Place on table",
    "只能放到相邻的台面上。": "You can only place items on an adjacent platform.",
    "这块台面被机关或任务占用，不能往上放东西。":
        "That platform is claimed by a mechanism or task; nothing can be placed on it.",
    "携带意象仍在使用中，不能放到台面上。":
        "The carried image is in use and cannot be placed on a platform.",
    "旁边没有可以放东西的台面。": "There is no platform nearby to place things on.",
    "把 {item} 放在了台面上。": "Placed {item} on the platform.",

    # ---- 图鉴：物品/携带意象 effect id 的可读名称 ----
    "发射许可": "Fire license",
    "爆发推离": "Blast push",
    "火海": "Sea of Fire",
    "十字引燃": "Cross Ignition",
    "攻击附燃": "Striking Ignition",
    "火焰护符": "Fire Ward",
    "爆破扩径": "Blast Widening",
    "纵火亲和": "Arsonist's Affinity",
    "容器：盛装/倒出": "Container: fill / pour",
    "使用与投掷都进入落点瞄准：落点十字五格先泼上燃油（中心 12、四邻 6）再一起点燃，斜角四格只烧本来就可燃的格——整片 3×3 火海。已有液体的地面不另铺油，防火层点不着；落点选在脚下即原地释放。": "Use and throw both open landing aiming: the five cells of a cross at the landing point are doused in fuel oil (12 at the centre, 6 in the four neighbours) and light together, while the four diagonals burn only if they were already flammable — a full 3×3 fire sea. Ground that already holds liquid gets no extra oil, and fireproof tiling will not catch; aiming at your own feet releases it in place.",
    "落点（或脚下）十字五格点燃已有可燃材料的格子，干净地板不会自己烧起来；高浓度可燃气会被引爆。使用即进入落点瞄准，把落点选在自己脚下就是原地迸火星。": "Ignites the cells that already hold flammable material across the five cells of a cross at the landing point (or at your feet); clean floor will not catch fire on its own, and dense gas detonates. Using it opens landing aiming — choose your own cell and the sparks burst in place.",
    "近战与弹体命中后点燃目标所在格。": "Melee and projectile hits ignite the target's cell.",
    "站在火焰格不再受到清醒创伤。": "Standing in fire no longer costs clarity.",
    "投掷爆炸物与烈焰新星的半径 +1。": "Thrown explosives and the flame nova gain +1 radius.",
    "所有点燃来源的火焰强度 +1。": "Every fire you light burns with +1 strength.",
    "点燃": "Ignite",
    "放电": "Discharge",
    "恢复想象力": "Restores imagination",
    "弹体充能": "Projectile charge",
    "悄声无息": "Silent steps",
    "记忆回响": "Memory echo",
    "心智守护": "Mind guard",
    "修缮": "Repair",
    "恢复心智": "Restores mind",
    "恢复清醒": "Restores lucidity",
    "挂载替身": "Hung stand-in",
    "屏蔽声响": "Noise cut",
    "迟缓光环": "Slow aura",
    "照明": "Illumination",
    "测距": "Measure",
    "双重复原": "Split restore",
    "未知药效": "Unknown effect",
    "过热": "Overclock",
    "温热恢复": "Warm restore",
    "清醒回复": "Lucidity regen",
    "声响诱引": "Sound lure",
    "致盲闪光": "Blinding flash",
    "打滑": "Slick",
    "引燃液体": "Ignite liquid",
    "迟缓爆发": "Slow burst",
    "迟缓铃音": "Slow ring",
    "八向火星": "Eight-way sparks",
    "分层焦油": "Layered tar",
    "远程按键": "Remote press",

    "击退": "Knockback",
    "格挡": "Parry",
    "液面滑行": "Liquid glide",
    "落空一步": "Skipped step",
    "免费行动": "Free action",
    "免费移动": "Free move",
    "武器伤害": "Weapon damage",
    "心智护甲": "Mind armor",
    "清醒护甲": "Lucidity armor",
    "视野提升": "Vision up",
    "迅捷拾取": "Swift pickup",
    "修缮强化": "Repair boost",
    "穿透强化": "Pierce boost",
    "习得构想": "Learn ability",
    "永久显影": "Permanent development",
    "凝固虚空": "Coagulate the void",
    "双重护甲": "Dual armor",
    "迅捷攻击": "Swift strike",
    # 2026-10-18 材料效果与伤害下调
    "低语缠耳": "Whisper-Laced Ears",
    "凝胶滞足": "Gel-Locked Steps",
    "无菌隔护": "Sterile Barrier",
    "晨醒": "Morning Wake",
    "梦液滋养": "Dream Infusion",
    "油膜": "Oil Film",
    "淋巴暖流": "Lymph Warmth",
    "清兆": "Clear Omen",
    "电麻": "Static Numbness",
    "蜜愈": "Honey Mending",
    "酒雾": "Wine Haze",
    "骨酸": "Bone Ache",
    "凝胶基液黏住脚步：移动额外耗时 +0.2。":
        "Gel base sticks to your steps: +0.2 extra move time.",
    "无意识低语放大你的动静：声音传播半径 ×2。":
        "The unconscious whisper amplifies your movements: sound radius ×2.",
    "晨醒溶液让人一下坐直：每 4 回合恢复 0.5 点清醒。":
        "Morning-wake solution straightens you up: recover 0.5 lucidity every 4 rounds.",
    "每 4 回合：心智 -0.5、清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 7 回合退净。":
        "Every 4 rounds: mind -0.5, lucidity -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 7 rounds.",
    "每 4 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 3 回合退净。":
        "Every 4 rounds: mind -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 3 rounds.",
    "每 4 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。":
        "Every 4 rounds: mind -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 5 rounds.",
    "每 4 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。视野 +1。":
        "Every 4 rounds: mind -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 5 rounds. Vision +1.",
    "每 4 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。":
        "Every 4 rounds: mind -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 6 rounds.",
    "每 4 回合：想象力 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。视野缩到 50%（与遮蔽同类取最小倍率，不相乘至近零）。":
        "Every 4 rounds: imagination -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 6 rounds. Vision shrinks to 50% (ratios take the smallest multiplier across the same family; they do not multiply into near-blindness).",
    "每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。":
        "Every 4 rounds: lucidity -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 5 rounds.",
    "每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。视野 -2（尘族同族取最大，不叠成全盲）。":
        "Every 4 rounds: lucidity -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 5 rounds. Vision -2 (dust-family effects take the largest single penalty; they never stack into blindness).",
    "每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。崩解每回合 +1。":
        "Every 4 rounds: lucidity -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 6 rounds. Dissolution +1 per round.",
    "每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。攻击耗时 +0.5。":
        "Every 4 rounds: lucidity -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 6 rounds. Attack time +0.5.",
    "每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。静电尘中每回合额外清醒 −1。":
        "Every 4 rounds: lucidity -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 6 rounds. In static dust, extra lucidity -1 per round.",
    "每 5 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。攻击耗时 +0.3。":
        "Every 5 rounds: lucidity -0.5 (heavier with depth). Lingers 2 rounds after leaving, then fades over 6 rounds. Attack time +0.3.",
    "注射用梦水缓缓渗入：每 4 回合恢复 0.5 点心智。":
        "Dream water for injection seeps in: recover 0.5 mind every 4 rounds.",
    "消兆薄雾把杂念洗淡：每 4 回合恢复 0.5 点清醒（随深度）。":
        "Omen-clearing mist washes away stray thoughts: recover 0.5 lucidity every 4 rounds (with depth).",
    "淋巴液推着循环：每 4 回合恢复 0.5 点清醒（随深度）。":
        "Lymph pushes the circulation: recover 0.5 lucidity every 4 rounds (with depth).",
    "燃油在鞋底打滑：移动额外耗时 +0.15。":
        "Fuel oil slips under your soles: +0.15 extra move time.",
    "电浆雾的余电钻进指尖：移动额外耗时 +0.15。":
        "Plasma mist's residual charge numbs your fingers: +0.15 extra move time.",
    "红酒的香气缠上来：每 5 回合清醒 -0.5（随深度），攻击耗时 +0.2。":
        "Wine aroma clings to you: every 5 rounds lucidity -0.5 (with depth), attack time +0.2.",
    "蚀骨瘴黏在关节上：移动额外耗时 +0.15。":
        "Bone-eating miasma sticks to your joints: +0.15 extra move time.",
    "蜜酿润过喉咙：每 4 回合恢复 0.5 点心智（随深度）。":
        "Honey brew soothes your throat: recover 0.5 mind every 4 rounds (with depth).",
    "行动速度 ×1.4；不再造成清醒流失。离开材料后加速还会维持 5 回合。":
        "Movement speed ×1.4; no longer drains lucidity. The boost lasts 5 rounds after leaving the material.",
    "行动速度 ×1.5；不再造成清醒流失。离开材料后加速还会维持 5 回合。":
        "Movement speed ×1.5; no longer drains lucidity. The boost lasts 5 rounds after leaving the material.",
    "过滤后的载气隔开侵蚀：心智流失减少 20%。":
        "Filtered carrier gas blocks erosion: mind loss reduced by 20%.",
}

# ---- o 键目标辅助 / 瞄准辅助 ----
EN_ASSIST: dict[str, str] = {
}

# ---- 开局选项页（2026-10-09）：织梦调律 / 择碎片入梦 ----
EN_RUN_OPTIONS: dict[str, str] = {
    '清醒': 'Lucidity',
    '想象': 'Imagination',
    '近战': 'Melee',
    '射击': 'Shooting',
    '投掷': 'Throwing',
    '构想': 'Conceive',
    '材料操作': 'Material Handling',
    '—— 身份能力 ——': '— Identity Abilities —',
    '借雾': 'Borrow Fog',
    '退稿': 'Retract',
    '常梦者': 'Ordinary Dreamer',
    '纸身旅人': 'Paper Traveler',
    '雨里住客': 'Rain Dweller',
    '余烬抄写者': 'Ember Scribe',
    '瓷壳修补匠': 'Porcelain Mender',
    '镜中替身': 'Mirror Double',
    '雾中旁观者': 'Fog Observer',
    '未署名的执笔者': 'Unsigned Writer',
    '—— 梦中身份与梦性 ——': '— Identity and Dream Points —',
    '梦性 {remaining}/{total} · 身份 {identity} · 加点 {upgrades} · 返还 {refund}/{nominal}':
        'Dream {remaining}/{total} · Identity {identity} · Tiers {upgrades} · Refund {refund}/{nominal}',
    '降档最多返还 3；身份与公共加点只共用梦性。': 'Refunds cap at 3; identity and aptitudes share dream points.',
    '必选一个完整身份；能力档位对所有身份相同。': 'Choose one whole identity; all share the same aptitude tiers.',
    '—— 独立能力加点 ——': '— Independent Aptitudes —',
    '继续：选择身份': 'Next: Identity',
    '确认调律后选择身份与能力档位。': 'Confirm tuning, then choose identity and aptitudes.',
    '梦性不足：保留草稿，请降低能力或改选身份。': 'Over budget: draft kept; lower aptitudes or change identity.',
    '出生上限': 'Starting cap',
    '构想成本': 'Conceive cost',
    '基础行动耗时': 'Base action time',
    '降档的名义返还与实际返还分别显示；确认不必花完。': 'Nominal and capped refunds are separate; unspent points are allowed.',
    '确认身份与加点后选择记忆；此时仍不创建存档。': 'Next choose a memory; no save is created yet.',
    '随机': 'Random',
    '默认': 'Default',
    '和大多数梦一样开始。均衡探索与自由构筑；没有额外的护持、弱点，也没有专属的本事。':
        'It begins like most dreams. Balanced exploration and open builds; no extra warding, weakness or special ability.',
    '你是由纸叠成的。失去追踪视线的移动留下半径 3 的旧位置声源，冷却 14；毒性附着缩短 20%，火焰创伤 +15%。你惯于绕着墙角走。':
        'You are folded from paper. Losing a pursuer\'s sight leaves sound at your old position (radius 3, cooldown 14). Poison attachment -20%; fire trauma +15%. You favor corners and lures.',
    '你习惯住在雨里。从液体走到干地时，一项同源负面附着减少 1，冷却 10；负面液体附着缩短 20%，电创伤 +15%。积水对你不是障碍。':
        'You live in the rain. Leaving liquid reduces one matching negative attachment by 1 (cooldown 10). Negative liquid attachment -20%; electric trauma +15%. Puddles never stop you.',
    '你用没烧完的火写字。亲手点燃未燃燃料后，3 回合内一次火焰直接创伤减 2，冷却 12；免疫燃烧征兆，电创伤 +15%。你总给自己留一条退路。':
        'You write with half-burnt fire. Igniting unlit fuel buffers one direct fire hit by 2 within 3 turns (cooldown 12). Immune to Burning portent; electric trauma +15%. You always keep an exit in mind.',
    '你的外壳是瓷的。亲手首次激活接收器恢复想象 2，每层最多两次、间隔 12；腐蚀附着缩短 20%，异象直接清醒创伤 +10%。你认得每一处机关的接缝。':
        'Your shell is porcelain. First player activation of a receiver restores 2 imagination, twice per layer with a 12-turn gap. Corrosion attachment -20%; direct anomaly lucidity trauma +10%. You know every seam of a mechanism.',
    '你从镜面那一侧来。记录实际直接受创最多 2，4 回合内下次普通近战追加等量创伤，记录冷却 12；负面视线附着缩短 20%，电创伤 +10%。你擅长把挨过的打还回去。':
        'You came from the other side of the mirror. Stores up to 2 actual direct trauma for your next normal melee hit within 4 turns (recording cooldown 12). Negative sight attachment -20%; electric trauma +10%. You return what you take.',
    '你站在雾的边缘。借雾：脚下黑烟 36，想象成本 5、冷却 14；免疫中毒征兆，异象直接心智创伤 +10%。退进雾里是你最熟的路。':
        'You stand at the edge of fog. Borrow Fog: 36 smoke at your feet, cost 5, cooldown 14. Immune to Poisoned portent; direct anomaly mind trauma +10%. Retreating into fog is your oldest habit.',
    '你的签名位置还空着。退稿：撤去相邻的本人构想墙，成本 4、冷却 14，每层首次恢复想象 2；火焰创伤 +10%。你习惯亲手改动地形。':
        'The signature line is still blank. Retract: remove an adjacent wall you conceived, cost 4, cooldown 14; first success per layer restores 2 imagination. Fire trauma +10%. You reshape terrain with your own hands.',
    '重置居中': 'Reset defaults', '继续：择碎片': 'Next: Memory', '返回': 'Back',
    '携带入梦': 'Enter dream', '梦境指标': 'Dream parameters', '强化': 'Boons', '挑战': 'Challenges',
    '冷却': 'Cooldown',
    '霜沿着脚蔓开：冻结了 {n} 个相邻的失控意识（{turns} 回合）。': 'Frost spreads from your feet: {n} adjacent uncontrolled minds freeze for {turns} turns.',
    '望远构想展开了：视野 +3，持续 {turns} 回合。': 'Farsight unfolds: sight +3 for {turns} turns.',
    '携带意象与你同频共振：{turns} 回合内效果放大 1.5 倍。': 'Your carried imagery resonates: effects are amplified 1.5 times for {turns} turns.',
    '↑↓ 选择 · ←→ 调整 · 空格开关 · 鼠标点击 · Esc 返回': 'Arrows adjust · Space toggle · Click select · Esc back',
    '难度仅描述这组选择，不是固定难度档位。': 'Difficulty reflects your choices; there are no fixed presets.',
    '选择一枚碎片后才创建存档；返回可继续调整。': 'The save is created after you pick a fragment. Back returns to tuning.',
    '确认调律后选择一枚记忆碎片。': 'Confirm your tuning, then choose a memory fragment.',
    '每回合回流': 'Regen/turn', '成本': 'Cost', '心智上限': 'Mind cap', '清醒上限': 'Lucidity cap',
    '想象力上限': 'Imagination cap', '受到创伤': 'Trauma taken', '运气修正': 'Luck', '数量': 'Count',
    '同组强化与挑战互斥，启用一项会关闭另一项。': 'Opposing choices are exclusive: enabling one disables the other.',
    '默认关闭；仅影响这一局。': 'Off by default; applies only to this run.',
    '想象力上限、回流速度、构想效力与成本': 'Imagination cap, regen, ability power and cost',
    '异象密度': 'Anomaly density', '构想节律': 'Ability tempo',
    '普通梦层的常规异象数量；机关与首领保持原编排': 'Regular anomaly count; puzzles and bosses keep their authored layout',
    '主动构想冷却时间；不缩短施放行动或异象预警': 'Active ability cooldown; actions and enemy warnings keep their timing',
    '疏落': 'Sparse', '偏疏': 'Scattered', '密集': 'Dense', '簇拥': 'Crowded',
    '偏慢': 'Unhurried', '轻快': 'Brisk', '灵动': 'Nimble',
    '宽阔记忆': 'Wide Memory', '封存记忆': 'Sealed Memory',
    '记忆碎片容量 +1': 'Memory fragment capacity +1', '记忆碎片容量 −1': 'Memory fragment capacity -1',
    '余响构想': 'Resounding Ideas', '淡薄构想': 'Faint Ideas',
    '构想效力再 +15%': 'Ability power +15% further', '构想效力再 −15%': 'Ability power -15% further',
    '迟滞异象': 'Drowsy Anomalies', '躁急异象': 'Hasty Anomalies',
    '异象主动技能冷却 +15%': 'Enemy active skill cooldown +15%',
    '异象主动技能冷却 −15%；预警不变': 'Enemy skill cooldown -15%; warning time unchanged',
    # 页面标题与帮助
    "—— 织梦调律 ——": "—— Dream Tuning ——",
    "—— 择一枚记忆碎片 ——": "—— Choose a Memory Fragment ——",
    "梦递来三枚残响，选其一随你入梦：": "The dream offers three echoes; choose one to carry in:",
    "↑↓ 选择 · Enter 携带入梦 · Esc 返回调律": "Up/Down choose · Enter carry into the dream · Esc back to tuning",
    "难度": "Difficulty",
    "就这样入梦": "Enter the dream like this",
    "↑↓ 选择 · ←→ 调整 · 空格/Enter 开关 · Enter(末行) 继续 · Esc 返回":
        "Up/Down choose · Left/Right adjust · Space/Enter toggle · Enter (last row) continue · Esc back",
    "全部选项均可自由调整，没有锁定。": "Every option is freely adjustable; nothing is locked.",
    "调律这一局梦": "Tune this dream",
    "←→ 调整指标 · 空格/Enter 开关 · Esc 返回": "Left/Right adjust · Space/Enter toggle · Esc back",
    # 滑条名与提示
    "异象强度": "Anomaly strength",
    "异象的完整度与造成的创伤": "Anomaly integrity and trauma dealt",
    "想象灵感": "Inspiration",
    "想象力上限、自然回流与构想成本": "Imagination cap, natural regen and ability cost",
    "意识强度": "Consciousness",
    "心智/清醒上限与抗击打能力": "Mind/lucidity caps and resilience",
    "思维流畅": "Mental fluency",
    "刷新物品时的运气（稀有度权重）": "Luck when refreshing items (rarity weights)",
    # 滑条档位：异象强度
    "沉寂": "Dormant", "偏弱": "Faint", "标准": "Standard", "活跃": "Restless", "狂暴": "Feral",
    # 滑条档位：想象灵感
    "枯竭": "Wilted", "稀薄": "Thin", "常流": "Flowing", "丰盈": "Abundant", "涌泉": "Gushing",
    # 滑条档位：意识强度
    "脆弱": "Fragile", "单薄": "Frail", "稳健": "Steady", "坚韧": "Tough", "不朽": "Undying",
    # 滑条档位：思维流畅
    "凝滞": "Clogged", "涩滞": "Sluggish", "常态": "Normal", "流畅": "Fluent", "泉思": "Effortless",
    # 开关
    "迟滞崩解": "Slow Decay",
    "崩解度增速 −25%": "Dissolution gain −25%",
    "坚韧自我": "Steady Nerves",
    "受到异象的创伤再 −15%": "Anomaly trauma taken −15% further",
    "明晰构想": "Clear Conception",
    "构想的想象成本再 −20%": "Ability imagination cost −20% further",
    "躁动之梦": "Restless Dream",
    "崩解度增速 +25%": "Dissolution gain +25%",
    "百目紧盯": "A Hundred Watching Eyes",
    "异象的视野 +2": "Anomaly vision +2",
    "浅眠": "Light Sleeper",
    "心智/清醒上限 −15": "Mind/lucidity caps −15",
    # 三层信息与知识来源（2026-10-18 docs 第 1 节第二批）
    "未探索": "Unexplored",
    "记忆": "Memory",
    "全图地形": "Full terrain",
    "始终可见": "Always visible",
    "来源：未探索": "Source: unexplored",
    "来源：记忆": "Source: memory",
    "来源：全图地形": "Source: full terrain",
    "来源：始终可见": "Source: always visible",
    "始终可见：": "Always visible: ",
    "未探索：这里没有留下确认过的地形。":
        "Unexplored: no confirmed terrain has been recorded here.",
    "实时变化不会改写记忆；再次看见才会更新。":
        "Live changes never rewrite memory; it updates only when seen again.",
    "未知固体": "Unidentified solid",
    "已发现地点：": "Discovered site: ",
    "设施": "facility",
    # 属性定义/解析（2026-10-18 docs §10 第二批）
    "点": "points", "回合/格": "turns/tile", "回合/次": "turns/hit",
    "倍": "×", "倍率": "multiplier", "格": "tiles", "权重": "weight",
    "点/回合": "points/turn",
    "{n:g} 回合/格": "{n:g} turn/tile",
    "基础规则 +1": "Base rule +1",
    "蜂蜜/传送带/免费步等条件另结算":
        "Honey, conveyor belts, free steps and similar conditions are settled separately",
    "贴近悔恨之锚": "next to the Anchor of Regret",
    "迟滞按欠账累计：积满 1 点才多花 1 回合":
        "Delay accumulates as debt: a full point costs one extra turn",
    "多种速度征兆叠乘并受既定上下限约束":
        "Speed portents multiply and are bounded by their existing caps",
    "夜视 +1": "Night vision +1",
    "边界脚本 +1": "Boundary script +1",
    "灯塔透镜 +3": "Lighthouse lens +3",
    "夜灯电池 +{n}": "Night-lamp battery +{n}",
    "记忆碎片 +{n}": "Memory fragment +{n}",
    "无光绒墙 {n}": "Lightless velvet wall {n}",
    "脚下反光地面 +{n}": "Reflective floor underfoot +{n}",
    "望远 +3": "Farsight +3",
    "征兆视野 {n}": "Portent vision {n}",
    "出生/记忆/开局调律": "Birth, memories or run tuning",
    "摇篮曲使自然回流暂停": "A lullaby pauses natural recovery",
    "留白线见底时额外 +{n}": "Blank-edge lines add +{n} when empty",
    "开局调律·想象灵感": "Run tuning · Inspiration",
    "心智档位 {n}": "Mind tier {n}",
    "心智档位": "Mind tier",
    "清醒档位": "Lucidity tier",
    "心智流失倍率": "Mind loss multiplier",
    "心智流失免疫": "Mind loss immunity",
    "投掷距离": "Throw range",
    "开局调律·思维流畅": "Run tuning · Fluency",
    "开局调律·意识强度（{tier}）": "Run tuning · Consciousness ({tier})",
    # 耐受与环境（docs §10 第四批）
    "身份弱点 {identity} · {channel} +{n}":
        "Identity weakness {identity} · {channel} +{n}",
    "火焰缓冲将抵消 {n}": "Fire buffer will offset {n}",
    "同类耐受取最高，不叠加成完全免疫":
        "Same-type tolerance takes the highest value and never stacks into full immunity",
    "耐受使新沾染时长缩短 50%、向上取整且至少 1 回合":
        "Tolerance shortens new exposure by 50%, rounded up and at least 1 round",
    "若恰好触发一次免疫，会再缩短并消耗该资格":
        "If a one-time immunity triggers, it shortens further and is consumed",
    "没有基础创伤": "No base trauma",
    "身份 {identity}": "Identity: {identity}",
    "只对本身份的对应环境通道生效":
        "Applies only to this identity's matching environment channel",
    "多个减半类征兆取最小倍率，对一切来源生效":
        "Multiple halving portents take the smallest multiplier against all sources",
    "镇静只拦环境来源，不拦异象战斗创伤":
        "Calm blocks environment sources only, not anomaly combat trauma",
    "同类耐受取最高，不叠加": "Same-type tolerance takes the highest value; no stacking",
    # 构想/篡改/缓冲（docs §10 第五批）
    "出生梦性·构想": "Birth dream-type · Conception",
    "开局调律·构想节律": "Run tuning · Conception rhythm",
    "思维润滑 −1": "Mental lubrication −1",
    "保留最低 1 回合；冷却进度不因查看面板刷新":
        "Minimum 1 round; cooldown progress is not refreshed by viewing the panel",
    "连续压力 {n}/3": "Continuous pressure {n}/3",
    "最终值 = ceil(基础混乱 × 1.3) + 压力 × 2；预览不判定风险":
        "Final = ceil(base chaos × 1.3) + pressure × 2; preview does not roll risk",
    "缓冲类型：{kind}": "Buffer type: {kind}",
    "只抵下一次对应创伤，不恢复资源":
        "Offsets only the next matching trauma; does not restore resources",
    # 地图显示模式（2026-10-18 docs 第 13 节）
    "自动（推荐）": "Auto (recommended)", "图像": "Image", "字符": "Character",
    "当前构建尚未接入图像地图": "This build does not include the image map yet",
    "玩家选择字符地图": "Character map selected",
    "图像地图可用": "Image map available",
    "图像不可用，已回退字符：{reason}":
        "Image map unavailable; using character map: {reason}",
    "自动回退字符地图：{reason}": "Auto fallback to character map: {reason}",
    "图像预览": "Image preview",
    "当前不在 WezTerm 中运行": "Not running inside WezTerm",
    "找不到随包 wezterm.exe": "Bundled wezterm.exe not found",
    "图像地图预览：按 Enter 返回游戏":
        "Image map preview: press Enter to return to the game",
    "图像预览失败：{error}": "Image preview failed: {error}",
    "分层观察": "Observation layer",
    "综合": "Composite", "地形": "Terrain",
    "图像预览/分层观察显示哪一层：综合、地形、液体或气体。":
        "Which layer the image preview shows: composite, terrain, liquid or gas.",
    "分层观察：{label}": "Observation layer: {label}",
    "同格内容": "On this cell", "另有 {count} 层": "{count} more layer(s)",
    "对象与任务": "Objects & tasks",
    "原色": "Original colors",
    "生物×{count}": "{count} actors", "物品×{count}": "{count} items",
    "事件×{count}": "{count} events",
    # 自我察觉第六批：分类/来源/近期变化
    "总览": "Overview", "行动": "Actions", "攻防": "Offense & defense",
    "感知": "Perception", "恢复": "Recovery", "构想/篡改": "Abilities / tamper",
    "环境": "Environment", "来源": "Sources",
    "（我的状态·来源·近期变化）": " (status, sources, recent changes)",
    "←→ 切换分类 · ↑↓ 选择 · Enter/空格 展开 · Esc 关闭":
        "←→ switch category · ↑↓ select · Enter/Space expand · Esc close",
    "这个分类暂时没有可显示的内容。": "Nothing to show in this category yet.",
    "无额外来源或条件。": "No extra sources or conditions.",
    "近期变化（有界内存，不写存档）": "Recent changes (bounded memory, not saved)",
    "尚无资源结算记录。": "No resource settlements recorded yet.",
    "心理状态": "Mental state", "主要限制": "Main limits",
    "心智 {mind} · 清醒 {lucidity} · 想象 {imagination}":
        "Mind {mind} · Lucidity {lucidity} · Imagination {imagination}",
    "心智失控（{tier}）": "Mind unstable ({tier})",
    "清醒不稳（{tier}）": "Lucidity unstable ({tier})",
    "心智流失被镇静拦截（环境来源）":
        "Mind loss blocked by calm (environment sources only)",
    "附着征兆 {n} 种": "{n} attached portents",
    "无显著限制": "No significant limits",
    "限制按实际规则生成，不使用写死的档位故事":
        "Limits are generated from actual rules, not hardcoded tier stories",
    "已生效装备": "Active equipment", "记忆碎片": "Memory fragment",
    "洞察": "Insight", "征兆 · 剩余 {n} 回合": "Portent · {n} rounds left",
    "开局调律": "Run tuning", "本局": "this run", "生效": "active",
    "携带": "carried", "常驻": "permanent", "附着": "attached",
    "身份环境弱点": "Identity environment weakness",
    "基础值：": "Base: ", "来源：": "Source: ", "说明：": "Note: ",
    "是": "Yes", "否": "No", "可用": "Available", "不可用": "Unavailable",
    "当前生效": "Active now", "当前未生效": "Not active now",
    "无（无对应弱点）": "None (no matching weakness)",
    "移动": "Move", "攻击": "Attack", "使用": "Use", "免费": "Free", "杂项": "Misc",
    "额外 {n:g}": "extra {n:g}",
    "行动 {kind}：基础 {base:g} → 实付 {paid:g}{extra}":
        "Action {kind}: base {base:g} → paid {paid:g}{extra}",
    # 增强项（2026-10-18 docs 第 1 节）：不参与难度
    "增强": "Enhancements",
    "全图地形": "Full Terrain Map",
    "整层地形布局与类型已知（仅地形，不含生物、物品与环境细读）":
        "The whole layer's terrain layout and types are known (terrain only; no creatures, items or environment readings).",
    "开启后可按当前层地形规划路线；不授予攻击或交互资格，不伪造普通探索进度。":
        "Plan routes from the current layer's terrain; grants no attack or interaction rights and never forges exploration progress.",
    "（不改变难度）": " (no difficulty change)",
    "三层信息": "Three-layer information",
    "未探索区域显示黑幕，已探索区域保留暗色地形记忆，当前视野保持完整。":
        "Unexplored areas show black, explored areas keep a dim terrain memory, and the current sight stays complete.",
    "不改世界规则与难度；只改变地图与格子详情显示的信息权限，可随存档保存。":
        "Changes no world rules or difficulty; only the information rights of the map and cell details, saved with the run.",
    # 难度区间命名
    "轻松": "Gentle", "偏轻": "Mild", "中等": "Moderate", "偏重": "Heavy", "沉重": "Grim", "噩梦": "Nightmare",
    # 结算与引导消息
    "你携着「{item}」的残响入梦。": "You enter the dream carrying the echo of {item}.",
    "入梦结束。已形成的记忆碎片收进了梦的夹层。":
        "The dream ends. The memory fragments you formed settle into its lining.",
    # ---- 携带意象·联想盘编辑器（设计方案 §8） ----
    "联想 v": "Links v",
    "装配 v": "Board v",
    "词义 m": "Meaning m",
    "原意 c": "Original c",
    "安置 A": "Auto-place A",
    "旋转 r/中键": "Rotate r/middle-click",
    "拆除 x/右键": "Remove x/right-click",
    "确认 Enter": "Confirm Enter",
    "确认整理": "Confirm",
    "选中意象": "Selected image",
    "原意（握持）": "Original (wielded)",
    "原意": "Original",
    "意象（只提供语义）": "Image (semantics only)",
    "我用{item}命中目标，保留原攻击规格与成本。": "I strike with {item}, keeping its original attack and cost.",
    "{item}只提供「{semantics}」语义，不注册原效果。": "{item} supplies {semantics} semantics, without its original effect.",
    "我承载{item}：{effect}": "I carry {item}: {effect}",
    "先选中盘上或手中的意象，再切换词义。": "Select a board or held image to change its meaning.",
    "先选中盘上或手中的意象，再写出或撤回原意。": "Select a board or held image to write or withdraw its original sense.",
    "词义：{meaning}": "Meaning: {meaning}",
    "原意已写出，确认后生效。": "Original sense written; it takes effect after confirmation.",
    "原意已撤回：只占空间，不提供效果或语义。": "Original sense withdrawn: occupies space, supplies no effects or semantics.",
    "m 切词义 · c 写出/撤回原意\n原意恢复旧行为，意象词义只参与联想。": "m changes meaning; c writes/withdraws the original.\nOriginal retains old behavior; image meaning supplies semantics only.",
    "想象 {cost} · 冷却 {cd}": "Imagination {cost} · Cooldown {cd}",
    "缺少{semantic}语义，当前不触发。": "Missing {semantic} semantics; cannot trigger.",
    "只有事件格存在有效导电液体时才通过。": "Passes only when the event cell has a conductive liquid.",
    "只通过目标／触发位置存在有效导电液体的事件。": "Passes only when the target or event cell has a conductive liquid.",
    "下一次对应创伤减少 1，最多存 1 点，最多保持 3 回合。": "Reduces the next matching trauma by 1; stores one point for up to 3 turns.",
    "从事件位置真实液体转移最多 5 单位到一个合法相邻格。": "Moves up to 5 units of actual liquid from the event cell to a legal neighbor.",
    "给一个合法湿润敌人 1 点完整度反馈。": "Deals 1 integrity damage to a legal wet enemy.",
    "只有想象力不高于线路上留白装备的原阈值才通过；无对应装备时取系统阈值 10。": "Passes below the linked blank item's imagination threshold; defaults to 10 without one.",
    "需要拍语义：保存一个事件，2 个客观回合后释放；只留一个，后来事件不覆盖；4 回合内过期。": "Requires beat semantics: stores one event, releases after 2 turns, never overwrites it; expires within 4 turns.",
    "一入两出：两支共用原预算与总资源；不足时按预览中的优先次序选一支。": "One input, two outputs: both share the original budget and resources; limited resources follow preview order.",
    "在一个合法可燃格调用现有点燃入口，输入强度不超过 1；只发一次，后续燃烧走原模拟。": "Ignites one legal fuel cell at strength 1 or less, once; subsequent burning uses the normal simulation.",
    "在事件格／上一位置产生半径不超过 2 的一次声源，复用既有引诱规则；不硬控、不伤害。": "Makes one sound at the event or previous cell, radius at most 2, using existing lure rules; no stun or damage.",
    "湿": "Wet", "电": "Electric", "热": "Heat", "声": "Sound",
    "护": "Guard", "照": "Light", "拍": "Beat", "空": "Blank",
    "联想盘边框必须是 8×6 格": "The board must have an 8x6 border",
    "存档中的联想盘布局无效；意象仍在行囊中，请重新整理。": "The saved board layout is invalid; all imagery remains in the backpack. Please rearrange it.",
    "盘上词块与行囊实例不符": "Board word does not match its backpack instance",
    "握持焦点必须是已成句的行动意象": "Focus must be a formed action image",
    "整理联想盘": "Arrange the board",
    "[ 编辑联想盘": "[ Edit the board",
    "{paths} 条通路 · {broken} 处未成句 · [ 编辑": "{paths} paths · {broken} unformed · [ edit",
    "（草稿：确认整理前不生效、不耗时）":
        " (draft: nothing takes effect or costs time until you commit)",
    "联想视图": "Links view",
    "装备视图": "Equipment view",
    "工具 z": "Tools z",
    "握持 f": "Wield f",
    "自动安置 a": "Auto-place a",
    "取消 Esc": "Cancel Esc",
    "{name}里的{medium}": "{medium} in the {name}",
    "喷出": "spray out",
    "if {condition} → row {n}": "if {condition} -> row {n}",
    "toward {target} → row {n}": "toward {target} -> row {n}",
    "盘面还空着：把行囊里的携带意象摆上来就能成句。": "The board is empty: place carried imagery on it to form sentences.",
    "方向键移动 · a拿放/安置 · 空格取列表项 · ,/.选列表\n"
    'x或右键拆除 · r或中键旋转 · z功能词 · v详情 · A自动安置\n'
    'Enter确认（耗时一次） · Esc放回/取消 · 预览免费':
        "Arrows move · A pick/place · Space takes list item · ,/. browse\n"
        "x/right-click removes · r/middle-click rotates · z words · v details\n"
        "A auto-place · Enter confirm (one action) · Esc cancel · free preview",
    "空手（搬动意象）": "Bare hands (move imagery)",
    "接梦线·直": "Dream wire · straight",
    "接梦线·弯": "Dream wire · corner",
    "工具：{tool}": "Tool: {tool}",
    "拿起了 {tool}。": "Picked up {tool}.",
    "拿起了 {item}：方向键移动，r 旋转，a 放下。":
        "Picked up {item}: arrows to move, r to rotate, A to place.",
    "拿起了 {item}（{area} 格）：方向键移动，r 旋转，a 放下。":
        "Picked up {item} ({area} cells): arrows to move, r to rotate, A to place.",
    "这一格是空的：用 , / . 选中下方列表里的一件再按空格拿起，或按 z 取用工具后 a 铺线。":
        "This cell is empty: use , / . to select an entry below and Space to pick it up, "
        "or press z for a tool then A to lay wire.",
    "越过盘面边框：{held} 放不进这个位置。": "Past the board edge: {held} does not fit here.",
    "这些格已经被占了：{held} 放不下（不自动挤掉其他件）。":
        "These cells are taken: {held} does not fit (other pieces are never squeezed out).",
    "行囊里没有可上盘的携带意象。": "No board-ready carried imagery in the backpack.",
    "放回原位。": "Put back where it was.",
    "松手了：{held} 仍在行囊里。": "Let go: {held} is still in the backpack.",
    "已卸下 {held}。": "Removed {held}.",
    "已卸下 {item}。": "Removed {item}.",
    "这一格没有可拆除的东西。": "Nothing to remove on this cell.",
    "拆掉了这段接梦线。": "Removed this dream wire.",
    "拆掉了这块插片。": "Removed this insert.",
    "{item}已经在盘上了。": "{item} is already on the board.",
    "找不到能放下 {item} 的合法位置：{area} 格的形状与现有摆放冲突，先挪开或拆除一些实体再试。":
        "No legal spot for {item}: its {area}-cell shape conflicts with the current layout. "
        "Move or remove something first.",
    "自动安置 {item} 到 ({x},{y})，旋转 {rotation}°。":
        "Auto-placed {item} at ({x},{y}), rotation {rotation}°.",
    "把光标移到盘上一件意象上再切换握持。":
        "Move the cursor onto a piece on the board before switching the wielded one.",
    "{item}还没有写出原意，不能握持。":
        "{item} has no written original sense yet, so it cannot be wielded.",
    "{item}不是可握持的行动意象。": "{item} is not a wieldable action image.",
    "联想盘 {used}/{total} 格": "Association board {used}/{total} cells",
    "成句 {sentences}": "Sentences {sentences}",
    "联想盘 {used}/{total} · 成句 {sentences}": "Board {used}/{total} - {sentences} sentences",
    "成句": "Sentences",
    "握持 {name}": "Wielding {name}",
    "工具 {tool}（z 切换）": "Tool {tool} (z to switch)",
    "光标 ({x},{y}) · 旋转 {rotation}°": "Cursor ({x},{y}) · rotation {rotation}°",
    # ---- 落点与优先方向（§5.5 要求的编辑器控制） ----
    "事件格": "event cell",
    "玩家格": "player cell",
    "上一移动格": "previous cell",
    "近处可见敌人": "nearest visible enemy",
    "北": "north",
    "东": "east",
    "南": "south",
    "西": "west",
    "光标下没有插片：先按 z 取用工具，再按 a 把它铺在光标格。":
        "No piece under the cursor: press z to take a tool, then Enter to lay it down.",
    "{tool} 没有落点档位：它不在盘面之外挑格子。":
        "{tool} has no destination setting: it never picks a cell outside the board.",
    "落点：{policy}": "Destination: {policy}",
    "落点 {policy}（p）": "destination {policy} (p)",
    "只有移涌片有目的格优先方向：把光标停在移涌片上再按 j。":
        "Only the surge piece has a priority direction: park the cursor on it and press j.",
    "移涌优先方向：{d}": "Surge priority: {d}",
    "水源固定为事件格 · 优先 {d}（j）":
        "source fixed to the event cell · priority {d} (j)",
    "{label} ({x},{y})": "{label} ({x},{y})",
    "已接线": "wired",
    "未接线": "not wired",
    "同效果 {n} 件：原值 {raw} → 递减后 {after}（−{loss}）":
        "{n} items share this effect: raw {raw} → {after} after diminishing (−{loss})",
    "{area} 格": "{area} cells",
    "（{area} 格）": "({area} cells)",
    "盘上意象：": "Imagery on the board:",
    "  入端 ({x},{y}) 朝 {d} · 出端 ({x2},{y2}) 朝 {d2}":
        "  in-port ({x},{y}) facing {d} · out-port ({x2},{y2}) facing {d2}",
    "朝 {d}": "facing {d}",
    "盘面外的根事件端：": "Root event endpoints off the board:",
    "行囊中的携带意象（, / . 选中，空格拿起）：":
        "Carried imagery in the backpack (, / . to select, Space to pick up):",
    "已上盘": "on board",
    "在行囊": "in backpack",
    "手上：{held} · a 放下 · Esc 放回 · x 卸下":
        "In hand: {held} · Enter place · Esc put back · x remove",
    "手上：{tool} · a 铺在光标格": "In hand: {tool} · A lays it on the cursor cell",
    "空手：a 拿起光标下的意象": "Bare hands: A picks up the imagery under the cursor",
    "条件未满足": "condition unmet",
    "接梦：还没有连出通路——铺接梦线把意象接到插片上。":
        "Links: no path connected yet — lay dream wire from imagery to an insert.",
    # ---- 梦中梦·千禧园 M4（2026-10-10）：掉线拨号 + 零点体育场 ----
    "刺耳的调制音撕开梦面——网络邻居正在敲门。":
        "A harsh modem screech tears through the dream — the network neighbor is knocking.",
    "（{rounds} 回合内按「回应」应答，过时对面挂断。）":
        "({rounds} rounds to respond — after that, the other end hangs up.)",
    "拨号音停了——对面挂断了。":
        "The dial tone died — the other end hung up.",
    "你摘下听筒——握手音之后，世界换了一层旧漆。":
        "You pick up the handset — after the handshake, the world repaints itself in old plastic.",
    "你已拨入。屏幕上的进度条猛地跳完——千年虫顺着电话线爬出来了。":
        "You are connected. The progress bar slams to its end — the Millennium Bug crawls out along the phone line.",
    "终端静默——它已经出来了。":
        "The terminal stays silent — it is already out.",
    "屏幕弹出「孵化请求」——两只屏保气泡从进程里溢了出来。":
        "A 'spawn request' pops up — two screensaver bubbles overflow from the process.",
    "「进程繁殖」——两只传呼精灵沿着数据线孵化出来。":
        "'Process breeding' — two pager sprites hatch along the data lines.",
    "「系统迁移」——两只雪花观众随它一起搬了家。":
        "'System migration' — two static viewers move house along with it.",
    "屏幕闪过一行「系统迁移中……」——千年虫挪进了机房深处。":
        "The screen flashes 'migrating...' — the Millennium Bug slips deeper into the server room.",
    "千年虫蜷缩成一串乱码，主机「嗒」地停了机。":
        "The Millennium Bug curls into a string of mojibake; the tower clicks off.",
    "弹窗炸开——掉出一封「未读消息 99+」。":
        "The popup bursts — an 'Unread 99+' drops out.",
    "垃圾传真嗡鸣作响——{n} 只异象循声锁定了你的位置。":
        "Junk fax screeches — {n} anomalies lock onto your position.",
    "磁带倒卷的吱嘎声缠上你的脚步（移动额外耗时 +0.2）。":
        "The whir of rewinding tape winds around your steps (+0.2 move time).",
    '脚步声响半径：{n}': 'Footstep sound radius: {n}',
    '足音消音 −1': 'Muffled footsteps -1',
    '行动': 'Action',
    '意志': 'Will',
    '完整度': 'Integrity',
    '浓度': 'Concentration',
    '存在': 'Existence',
    '插入点：{name} · {point}': 'Insertion: {name} / {point}',
    '改后：{sentence}': 'After: {sentence}',
    '改后': 'After',
    '改后：': 'After: ',
    '完整度 {n} · {alert}': 'Integrity {n} · {alert}',
    '选词：{word}': 'Word: {word}',
    '[确认]': '[Confirm]',
    '[取消]': '[Cancel]',
    '{sentence}。': '{sentence}.',
    '地面（{x},{y}）': 'Ground ({x},{y})',
    '拨开门纹': 'Open gate mechanism',
    '门纹让出了通路，这一次的解法已记下。': 'The gate opens a passage. This solution has been recorded.',
    '这道门纹已经让出了通路。': 'This gate has already opened a passage.',
    '门纹的结构已经改变，拨片带不动它。': 'The gate structure has changed; its lever cannot move it.',
    '你拨开门纹，纸墙收进了地面。': 'You operate the lever. The paper walls retract into the ground.',
    '门纹已让出通路，解法已经记下；再次处理不会重复结算。': 'The passage is open and the solution is recorded. Repeating it grants no further credit.',
    '门纹拨片：相邻操作可收起纸墙。可绕行来拨开，或点燃、打穿、篡改纸墙。': 'Gate lever: operate it from an adjacent tile to retract the paper walls. Go around to reach it, or burn, breach, or tamper with the walls.',
    '纸墙挡住近路：另一侧的拨片能收起它；也可点着、用弹体打穿或改写。外圈始终可绕。': 'Paper walls block the shortcut. A lever on the far side retracts them; fire, projectiles, or tampering also work. The outer route stays open.',
    '这里有人或物，不能凝成实墙。': 'An occupant or object is here; it cannot become a solid wall.',
    '这里承载着设施或机关，不能凝成实墙。': 'A facility or mechanism occupies this ground; it cannot become a solid wall.',
    '地面': 'Ground',
    '〔{name}〕将循着低语调查': '{name} will investigate the whisper',
    '〔{name}〕将循声靠近': '{name} will approach the voice',
    '〔{name}〕将应着尖声追来': '{name} will pursue the clamor',
    '〔{name}〕将惊散 {n} 回合': '{name} will be spooked for {n} turns',
    '〔{name}〕将失去 {n} 点完整度': '{name} will lose {n} integrity',
    '〔{name}〕将只剩原量的 1/{n}': '{name} will fall to 1/{n} of its volume',
    '〔{name}〕将被抹去': '{name} will be erased',
    '蜂鸣回响 +2': 'Humming echo +2',
    '深渊回声 +2': 'Abyssal echo +2',
    '眼前的情形已经改变，请重新选择。': 'The scene has changed. Choose again.',
    '这件东西牵着尚未结束的梦，不能抹去。': 'This object is tied to unfinished dreams and cannot be erased.',
    '低声招引': 'Whisper',
    '引向此处': 'Lure here',
    '对话与地图中打开篡改面板的按键。': 'Open the tamper editor in dialogue or on the map.',
    '改写对话或眼前的文字': 'Rewrite dialogue or the words before you',
    '在此鸣响': 'Echo here',
    '去向': 'Destination',
    '声源': 'Sound source',
    '熄灭光源': 'Extinguish light',
    '点亮光源': 'Light source',
    '光源已点亮。': 'The light is on.',
    '光源已熄灭。': 'The light is off.',
    '这里没有可以切换的光源。': 'There is no switchable light here.',
    '这盏灯靠燃烧发光——点火或灭火，而不是拨开关。':
        'This lamp burns for its light — light it or put it out, not flip a switch.',
    '灯架的电源接在电路上，这里没有可以拨的开关。':
        'The rig draws from the circuit; there is no switch to flip here.',
    '积液通向深处的显化物；一盏灯照着那里，另一侧留着一条干路。':
        'A pool leads toward a manifestation deeper inside. A lamp lights it; a dry route runs along the other side.',
    '光源：亮着，可在相邻操作中熄灭。': 'Light: on. Switch it off using an adjacent action.',
    '光源：靠燃烧发光，点着与浇灭决定明暗。':
        'Light: it burns for its glow — lighting it and putting it out decide the brightness.',
    '光源：接在电路上，通电才亮、断电即灭。':
        'Light: wired into the circuit — it shines only while powered.',
    '光源：熄灭，可在相邻操作中点亮。': 'Light: off. Switch it on using an adjacent action.',
    '让句子里的异象前往所选环境格调查；若它看见你，仍会重新追踪你。':
        'The anomaly in this sentence investigates the selected environment cell. Seeing you can restore pursuit.',
    '所选环境格发出基础半径 6 的声音；周围异象按距离听见并调查。':
        'The selected environment cell emits sound with base radius 6; nearby anomalies react according to distance.',
    '〔{actor}〕将前往〔{destination}〕调查。': '{actor} will investigate {destination}.',
    '〔{name}〕将响起声音，引来附近的注意。': 'Sound from {name} will attract nearby attention.',
    '〔{actor}〕开始向〔{destination}〕调查。': '{actor} starts investigating {destination}.',
    '声音从〔{name}〕所在的位置响起。': 'A sound rises from the location of {name}.',
    '这句话里没有可以招引的异象。': 'This sentence has no anomaly to lure.',
    '它正在紧追你，不会分心调查别处。': 'It is pursuing you and will not investigate elsewhere.',
    '那个位置无法作为调查落点。': 'That position cannot be an investigation destination.',
    '它已经站在那儿了。': 'It is already standing there.',
    '它还在惊散中，无法循线调查。': 'It is still spooked and cannot investigate a lead.',
    '那个位置已经被占据。': 'That position is occupied.',
    '固定异象后悬停环境，可改写两者的关系。':
        'Pin an anomaly and hover an environment cell to rewrite their relationship.',
    '它走不到那个位置。': 'It cannot reach that position.',
    '尖声呼唤': 'Clamor',
    '短暂退散': 'Brief dispersal',
    '深深退散': 'Deep dispersal',
    '剥落': 'Chip away',
    '崩碎': 'Shatter',
    '稀薄一半': 'Thin by half',
    '消散大半': 'Disperse most',
    '它会起疑并前往你此刻的位置调查，不会立刻锁定你。':
        'It becomes suspicious and investigates your current position, without immediately tracking you.',
    '它会追来；你脚下还会发出基础半径 8 的声音，附近异象也可能听见。':
        'It pursues you. Your position emits a sound with base radius 8; nearby anomalies may hear it.',
    '惊散 4 回合；受击会提前解除。': 'Spooked for 4 turns; a hit ends it early.',
    '惊散 10 回合；受击会提前解除。': 'Spooked for 10 turns; a hit ends it early.',
    '惊散 16 回合；受击仍会提前解除。': 'Spooked for 16 turns; a hit still ends it early.',
    '削去 25 点墙体完整度；崩塌仍会触发材料后果。':
        'Removes 25 wall integrity. Collapse still triggers material effects.',
    '削去 70 点墙体完整度；坚墙未必立即崩塌。':
        'Removes 70 wall integrity. Strong walls may remain standing.',
    '移走所选液体或气体的一半，保留剩余部分及其原有年龄。':
        'Removes half the selected liquid or gas, preserving the age of what remains.',
    '移走所选液体或气体的五分之四，保留少量残余。':
        'Removes four fifths of the selected liquid or gas, leaving a small residue.',
    '提交后混乱：{n}（{tier}）': 'Chaos after commit: {n} ({tier})',
    '它已经察觉了动静，低声招引不起作用。': 'It is already alert; a whisper will not distract it.',
    '这里已经没有可以稀释的东西。': 'There is nothing left here to thin.',
    '它循着低语前来调查。': 'It follows the whisper to investigate.',
    '你让「{name}」淡了下去。': 'You thin out {name}.',
    '封存气体': 'Sealed gas',
    '无吸入征兆': 'No inhalation portent',
    '可见残迹': 'Visible residue',
    '可吸入浓度': 'Breathable concentration',
    '浓气核心': 'Dense gas core',
    '{status} · 吸入门槛 ≥{threshold}': '{status} · Inhalation threshold ≥{threshold}',
    '（{syntax}）': '({syntax})',
    # M5（2026-10-10）：状态栏拨号倒计时（challenge_status 的 dial_status 通道）
    "网络邻居敲门 · 剩 {n} 回合":
        "Network neighbor knocking · {n} rounds left",
}
EN_UI.update({
 '常规': 'General', '画面': 'Display', '声音': 'Audio', '按键': 'Keys', '数据': 'Data',
 '新手教程': 'Tutorial', '发射来源': 'Firing sources', '操作提示': 'Controls',
 '余量 {count}': 'Supply {count}',
 '↑↓ 选择来源 · Enter/左键 设为当前': 'Up/Down select · Enter/click set source',
 'F 瞄准 · R 换弹': 'F aim · R reload',
 'Esc 退出瞄准': 'Esc cancel aim',
 '推荐终端未启动': 'Recommended terminal did not start',
 'F 瞄准 · R 换弹 · Esc 退出瞄准': 'F aim · R reload · Esc cancel aim',
 '瞄准中 ,/< 切换来源 · O 选择敌人': 'While aiming: ,/< sources · O enemy',
 'R换弹 · 其他键退出': 'R reload · Other keys exit',
 '弹药耗尽 · 任意键退出': 'Empty · Any key exits',
 'Tab/Shift+Tab 换页 · ↑↓ 选择 · ←→ 调整 · Enter/Space 修改 · Q 返回':
     'Tab/Shift+Tab pages · Up/Down select · Left/Right adjust · Enter/Space change · Q back',
 '教程中不修改正式记录。': 'Practice does not modify saved records.',
 '旧配置兼容项，不再生效；新手教程从普通存档栏独立进入。':
     'Legacy compatibility setting; tutorial is a separate entry below normal save slots.',
 '旧配置兼容项，不再生效；地图只保留小角标。':
     'Legacy compatibility setting; only compact intent badges remain.',
 '循环行动、行囊、构筑、自身、环境、日志；设置中换页': 'Cycle Act, Pack, Build, Self, Env, Log; change settings pages',
 '面板选择；←→ 切本区分类；Tab/Shift+Tab 循环六个大菜单；方向主键可在设置中修改':
     'Select entries; Left/Right change local categories; Tab/Shift+Tab cycle workspaces; movement keys are configurable',
 '瞄准中切换发射来源': 'Change firing source while aiming',
 'R 沿用开局快速再开 · T 独立新手教程 · 其他键返回主页':
     'R retry with the same choices · T standalone tutorial · Other keys return home',
    'PgUp/PgDn 滚动信息；Home/End 到首尾': 'PgUp/PgDn: scroll info; Home/End: top/bottom',
    '返回图像失败，已保留字符观察与草稿；F2 可重新选择地图模式。':
        'Image return failed. Character inspection and draft kept; use F2 to choose a map mode.',
    '图像恢复失败，暂用字符地图': 'Image restoration failed; temporarily using the character map',
})
EN_UI.update({
    '噪音': 'Noise', '混乱': 'Chaos', '噪音与混乱度': 'Noise and chaos',
    '本次预计声音': 'Sound forecast', '本格踩踏预计': 'Footstep on this tile',
    '下一步踩踏预计': 'Next footstep', '投掷落点预计': 'Throw landing',
    '一次性发射预计': 'Single-use projectile', '发射载荷预计': 'Projectile impact',
    '最终声径：{n} 格': 'Effective sound radius: {n} tiles',
    '落点未确定：最终声径暂不可知。': 'Impact unresolved: effective sound radius is unknown.',
    '20 是固定显示量程，不是声音上限，也不是统一警戒阈值。':
        '20 is a fixed display scale, not a radius cap or a universal alert threshold.',
    '发声点：({x},{y}) · 基础 {base} · 最终 {radius}':
        'Source: ({x},{y}) · Base {base} · Effective {radius}',
    '强诱引：可能直接引起追踪。': 'Strong lure: may trigger immediate pursuit.',
    '这里是行动预计，不是正在持续发声；0 只表示本次预计动作无声。':
        'This forecasts an action, not ongoing sound. Zero only means this action is silent.',
    '射击、投掷与声影可在远处发声；声径不等于玩家身体的暴露距离。':
        'Projectiles, thrown lures and echoes may sound elsewhere; this is not your detection radius.',
    '活动声影下一拍：({x},{y}) · 声径 {n}': 'Moving echo, next pulse: ({x},{y}) · Radius {n}',
    '平复进度：{n}/{m} · 距降低一点还需 {remaining} 合资格耗时':
        'Settling: {n}/{m} · {remaining} eligible action-time until chaos falls by one',
    '有效移动、攻击、使用的实付耗时计入平复；等待、免费查看、篡改自身不计入。':
        'Paid effective movement, attacks and uses count. Waiting, free inspection and tampering do not.',
    '连续篡改压力：{n}': 'Consecutive tamper pressure: {n}',
    '混乱度、连续压力和崩解度分别结算；心理状态也可能影响副作用。':
        'Chaos, tamper pressure and dissolution are separate; mental state can also affect side effects.',
    '篡改预览只报价，不提前增加实际混乱；这里只显示风险档位。':
        'Previewing a tamper does not add chaos. Only the visible risk tier is shown here.',
    '当前篡改报价：想象力 {cost} · 混乱 +{delta} → {after}':
        'Current tamper quote: imagination {cost} · Chaos +{delta} → {after}',
    # 混乱度「风险分档」说明（2026-10-27）：档位只描述副作用强度，概率不公开。
    # 逐档行由 signal_status.chaos_tier_lines 从 RISK_TIERS／TIER_EFFECTS 现拼。
    '风险分档': 'Risk tiers',
    '档位只描述副作用的强度，具体触发概率不公开；混乱越高，同一类副作用的数值越大。':
        'Tiers describe only how strong the side effects are; the actual trigger chance is not '
        'shown. The higher the chaos, the larger the numbers of the same side effects.',
    '{tier} {low}–{high}：{effects}': '{tier} {low}–{high}: {effects}',
    '{label}（清醒创伤 {n}）': '{label} (lucidity trauma {n})',
    '{label}（心智创伤 {n}）': '{label} (mind trauma {n})',
    '{label}（清醒 {lucidity}／心智 {mind}）':
        '{label} (lucidity {lucidity} / mind {mind})',
    '{label}（{n} 处）': '{label} ({n} patches)',
    '{label}（可能现身）': '{label} (may appear)',
    '混乱极高时，篡改可能召来专属混乱异象，它们也可能自行靠近。':
        'At extreme chaos, tampering may summon chaos-exclusive anomalies, and they may '
        'close in on their own.',
    '返回 · Esc / Alt+N': 'Back · Esc / Alt+N',
})

# 格子详情的逐对象清单（docs §16，2026-10-20）：权限来源、完整度上限来源、
# 独立计时、台面/地面位置与拾取条件。键是 ui/cell_detail.py 返回的中文口径，
# 显示点（panels._cd_creature_rows / _cd_item_rows）逐条经 tr() 取词。
EN_UI.update({
    # 存在性感知来源（§16.6：同一格里每个对象的权限分别判定）。
    '核心执念恒显': 'Always shown (core obsession)',
    '灵视揭示': 'Revealed by spirit sight',
    '自身': 'yourself',
    # 完整度上限的可信来源（§16.4：不拿内容表基础值冒充实例上限）。
    '实例记录': 'recorded for this instance',
    '出生值': 'spawn value',
    '本层已见': 'highest seen this floor',
    '内容表推算': 'estimated from the content table',
    '无内容表依据': 'no content-table basis',
    # 独立运行计时（§16.4：冻结/迟缓/失明各报剩余回合）。
    '冻结': 'Frozen',
    '失明': 'Blinded',
    '视野受限': 'Vision limited',
    '致盲：普通视觉归零': 'Blinded: ordinary sight is zeroed',
    '征兆视野 +{n}': 'Portent sight +{n}',
    '失焦 {n}（本项下限 {floor}）': 'Out of focus {n} (this entry floors at {floor})',
    '征兆缩视 ×{ratio}': 'Portent sight x{ratio}',
    '计时': 'Timers',
    '附着 {n} 回合': 'Attached for {n} rounds',
    # 位置与承载（§16.5）。
    '台面': 'Tabletop',
    '地表': 'Ground level',
    '上限：{source}': 'Cap: {source}',
    '表面身份': 'Surface identity',
    '强度': 'Strength',
    '只感知到存在：完整度、征兆与技能未经观察。':
        'Only its presence is sensed: integrity, omens and skills are unobserved.',
    '拾取条件：': 'Pickup: ',
    '用法：': 'Use: ',
    '现在就能取（G）': 'Ready to take now (G)',
    '走到台面旁边后从台面取下（G）':
        'Stand beside the tabletop, then take it off (G)',
    '走进这一格后拾取（G）': 'Step into this cell to pick it up (G)',
    '行囊已满（{used}/{capacity}），装不下的会留在原地。':
        'The pack is full ({used}/{capacity}); anything that does not fit stays here.',
    '入袋后可整理联想盘（U）· D 放下 · Q 投掷':
        'After taking: U arranges the board · D drops · Q throws',
    '入袋后可携带/卸下（U）· D 放下 · Q 投掷':
        'After taking: U equips or removes · D drops · Q throws',
    '入袋后可使用（U）· D 放下 · Q 投掷':
        'After taking: U uses · D drops · Q throws',
})

# §14 装备句法设置（2026-10-20）：只描述语序偏好，不是世界规则。
EN_UI.update({
    '装备句法': 'Equipment syntax',
    '中文语序': 'Chinese order',
    '英文语序': 'English order',
    '中文语序＝修饰在前、行为在四列；英文语序把行为前移到三列，宾语在后。'
    '只影响新盘面与词牌标签，不改变任何效果、费用或冷却。':
        'Chinese order puts modifiers first and the action in column four; '
        'English order moves the action to column three with the object after it. '
        'It only affects new boards and card labels — no effect, cost or cooldown changes.',
})

# Left-only spatial observation (2026-10-21).
EN_UI.update({
    '低层': 'Low', '中层': 'Middle', '高层': 'High',
    '图例': 'Legend', '关闭图例': 'Close legend', '地势观察': 'Elevation view',
    'F3 / Alt+V：分层观察；Alt+G：地势；观察内 Tab / [ ] 切层，\\ 图例，Esc 返回':
        'F3 / Alt+V: layers; Alt+G: elevation; Tab / [ ]: switch; \\: legend; Esc: return',
})

# Truthful firing-source HUD (magazine/reload integration remains pending).
EN_UI.update({
    '选择发射来源': 'Choose firing source', '来源已失效': 'Source unavailable',
    '一次性发射': 'Single-use shot', '发': 'shots',
    '按次消耗材料': 'Material per shot', '供给∞': 'Supply ∞',
    '当前发射源': 'Firing source', '待选择来源': 'Choose a source',
    '{count}种': '{count} sources',
    'O锁定 Tab落点 Esc退出': 'O lock · Tab cursor · Esc exit',
    'O锁定 Esc退出': 'O lock · Esc exit',
})

EN_UI.update({'当前来源无需换弹。': 'This source needs no reload.', '先按 F 选择要换弹的武器。': 'Press F to choose a weapon to reload.'})

EN_UI.update({'内置': 'Built-in', '每次{amount}': '{amount}/shot', '注入{amount}/{capacity}': 'Inject {amount}/{capacity}', '弹匣不足，请先换弹。': 'Not enough rounds in the magazine. Reload first.'})

EN_UI.update({'内置{cost}想': 'Innate {cost}i', 'R{done}/{total}已付': 'R{done}/{total} paid',
              'R{cost}想/{steps}步': 'R{cost}i/{steps}t'})


# 右侧面板同一按钮界面内的分层页签 + 操作界面·发射/篡改简版（2026-10-23）。
EN_UI.update({
    '面板选择（←→/WASD 先切本界面的分层页，到端才换按钮）；方向主键可在设置中修改':
        'Panel selection (left/right or WASD switches this panel\'s subpages first, then the button); directional keys can be remapped in Settings',
    '发射页只读：按 F 进入发射瞄准。': 'Fire page is read-only: press F to aim.',
    '目标：': 'Target: ', '装备': 'Equipment', '旧档继承': 'Legacy', '一次性': 'One-shot',
    '返回编辑：V / Esc': 'Back to editing: V / Esc',
    '装备盘': 'Equipment', '记忆碎片': 'Memories', '发射': 'Fire',
    '篡改': 'Tamper', '简版': 'Summary',
    '碎片槽满时拾到新碎片，会自动弹出替换界面。':
        'Picking up a fragment when the slots are full opens the replace screen.',
    '当前发射源': 'Current source',
    '—— 发射来源 ——': '— Firing sources —',
    '—— 换弹 ——': '— Reload —',
    '尚未解锁任何发射来源。': 'No firing source unlocked yet.',
    '没有可换弹的武器。': 'No reloadable weapon.',
    '当前不可发射': 'Cannot fire now',
    'F 进入发射瞄准 · Tab 切换来源 · R 换弹 · 发射按真实弹匣结算。':
        'F to aim · Tab switches source · R reloads · shots use the real magazine.',
    '原句：': 'Original: ',
    '可改写对象 {n} 处。': '{n} rewritable target(s).',
    '打开篡改界面（左侧）': 'Open tamper screen (left)',
    '按 C 打开完整篡改界面。': 'Press C for the full tamper screen.',
    '视野里没有可以改写的名字。': 'No rewritable name in sight.',
})


# Five-workspace sidebar (2026-10-23); business shortcut destinations are unchanged.
EN_UI.update({
    '构筑': 'Build', '自身': 'Self', '总览': 'Overview', '周围': 'Nearby',
    '记忆': 'Memory', '数值': 'Stats', '记录': 'Events', '清除搜索': 'Clear search',
    # 侧栏工具行后四个按钮（2026-10-25）：显示名由 _refresh_sidebar_tools 直给，
    # 这里补的是 tooltip 与 compose 时的取词。前三个单字按钮同理，避免
    # 「进游戏前 compose 出来是中文、刷新后才变英文」的闪烁。
    '折叠': 'Fold', '搜': 'Find', '类': 'Type', '序': 'Sort',
    '已学构想：{n}': 'Learned conceptions: {n}',
    '选择下方内容，或直接在地图行动。': 'Choose a section below, or act on the map.',
    '已装备 {n} 件': '{n} items equipped', '记忆碎片：{n}': 'Memory fragments: {n}',
    '已学洞察：{n}': 'Learned insights: {n}', '当前征兆：{n}': 'Active portents: {n}',
    '完整效果与数值来源可从下方查看。': 'Open Stats for full effects and their sources.',
    '结果：{n}': '{n} results',
    '没有匹配物品；点击上方 × 清除搜索，或切换分类。': 'No matches. Use × above to clear the search, or change category.',
    '需在联想盘中放置后确定': 'Determined after placement on the association board',
    '已选择': 'Selected',
})

EN_UI.update({
    '详查': 'Full details', '数值与来源': 'Stats and sources', '周围对象': 'Nearby objects',
    '视野中没有可列出的对象。': 'No known objects in sight.',
    '当前对象': 'Current focus',
    'Enter 查看选中对象的格子详情；F3 / Alt+V 分层观察。':
        'Enter opens the cell details of the selected object; F3 / Alt+V for observation layers.',
    '盘面占用：{used}/{total}': 'Board space: {used}/{total}',
    '面板选择（←→/WASD 切本区分类，到端停留；六区用上方文字按钮，原业务快捷键保留）；方向主键可在设置中修改':
        'Panel selection (Left/Right or WASD change categories and stop at the edges; use the five named tabs or existing direct shortcuts); movement keys are configurable',
})

EN_UI.update({'上一个右栏分区': 'Previous sidebar workspace', '下一个右栏分区': 'Next sidebar workspace'})

# 右侧「操作·篡改」完整编辑器（2026-10-28）：提交后保持界面、C 键切地图浮层、
# 以及旧简版摘要页移除后的空状态/重试入口。
EN_UI.update({
    '已切到地图侧篡改面板。': 'Switched to the map-side tamper panel.',
    '这次改写之后，眼前没有可以继续改写的名字了。':
        'After this rewrite, no name left in sight can be rewritten.',
    '按 C 打开地图侧篡改面板 / Enter 重试':
        'Press C for the map-side tamper panel / Enter to retry',
    '重试：打开篡改界面': 'Retry: open the tamper panel',
    '正在地图侧篡改。': 'Editing on the map side.',
    '这一句也能在右栏改：Esc 先回右栏。':
        'This line can also be edited in the right panel: Esc returns there first.',
})


# 测试模式存档栏（2026-10-23）：与普通槽位页同一套交互。
EN_UI.update({
    '测试存档栏': 'Test Saves',
    '测试模式：Enter 进入/新建 · R 替换（重新调律） · ←→ 选槽或删除 · 数字 1/2/3 直选 · Esc/Q 返回':
        'Test mode: Enter load/create · R replace (re-tune) · Left/Right slot or delete · 1/2/3 direct · Esc/Q back',
    '测试模式：删除后可新建；R 可直接用新的调律选项替换这一局（取消则旧档不变）。':
        'Test mode: delete then create, or press R to replace this run with new tuning options (cancelling keeps the old save).',
})

# 开局第三阶段「记忆编号（选填）」种子输入（2026-10-23）。
EN_UI.update({
    '记忆编号（选填）': 'Memory No. (optional)',
    'T/点击输入；留空随机，填整数作为本局种子':
        'T/click to edit; leave empty for random, or enter an integer as this run\'s seed',
    '↑↓ 选择记忆 · T/点击填写记忆编号（种子，选填） · Enter/入梦 · Esc 返回':
        'Up/Down: choose memory · T/click: memory number (seed, optional) · Enter: enter dream · Esc: back',
    '记忆编号需为 0–2147483647 的整数。':
        'Memory number must be an integer between 0 and 2147483647.',
    '记忆编号 {seed} 已作为本局种子。': 'Memory number {seed} is now this run\'s seed.',
})

# 并行会话新增的记忆管理/侧栏说明词条（2026-10-23）：补齐英文，保持 EN 渲染无中文。
EN_UI.update({
    '请先处理待收纳的记忆碎片。': 'Resolve the pending memory fragment first.',
    '无念黑渊吞掉了记忆，你想不起这些东西的用法。':
        'The Thoughtless Abyss swallowed the memory; you cannot recall how to use these.',
    '这条记忆已经不在槽中。': 'That memory is no longer slotted.',
    '行囊已满，无法取下记忆碎片。': 'The pack is full; cannot remove the memory fragment.',
    '已取下记忆：{name}。': 'Removed memory: {name}.',
    '这件物品已经不在行囊中。': 'That item is no longer in the pack.',
    '这件物品不是可装入的记忆碎片。': 'That item is not an insertable memory fragment.',
    '同一记忆已经装入。': 'The same memory is already installed.',
    '记忆槽已满，请先取下一条。': 'Memory slots are full; remove one first.',
    '已装入记忆：{name}。': 'Installed memory: {name}.',
    '需在联想盘中放置后确定': 'Place it on the association board to confirm',
    '仅比较物品实际字段，不预估未触发的组合。':
        'Compares actual item fields only; untriggered combinations are not predicted.',
})

EN_UI.update({
 '详情与操作':'Details and actions', '对比':'Compare', '弹匣':'Magazine', '当前配置':'Current loadout',
 '查看':'View', '完整操作':'Full actions', '查看全部数值来源':'Browse all stat sources',
 '配置来源目录（不代表均影响同一属性）':'Loadout sources (not all affect the same stat)',
 '装入记忆槽 · 1 回合':'Install memory · 1 turn', '取下至行囊 · 1 回合':'Remove to pack · 1 turn',
 '没有匹配的构想；可清除搜索或切换全部。':'No matching conceptions. Clear search or show all.',
 '搜索已学构想：名称、说明或标识；Enter/Esc 返回列表':'Search learned conceptions by name, description or ID; Enter/Esc returns.',
 '显示偏好仅在本次会话生效。':'Display preferences will apply only to this session.',
 '没有可显示的详情。':'No details available.', '行囊中没有此任务要求的具名物品。':'No matching named task item in the pack.',
 '这项委托已经不在进行中。':'This commission is no longer active.', '这项数值已经失效。':'This stat entry is no longer available.',
 '这项洞察已经失效。':'This insight is no longer available.', '请先处理待收纳的记忆碎片。':'Resolve the pending memory first.',
 '这条记忆已经不在槽中。':'This memory is no longer installed.', '行囊已满，无法取下记忆碎片。':'The pack is full; there is no room for this memory.',
 '这件物品不是可装入的记忆碎片。':'This item is not an installable memory.', '同一记忆已经装入。':'This memory is already installed.',
 '记忆槽已满，请先取下一条。':'Memory slots are full; remove one first.',
 '已取下记忆：{name}。':'Memory removed: {name}.', '已装入记忆：{name}。':'Memory installed: {name}.',
 '这件物品已经不在行囊中。':'This item is no longer in the pack.',
 '仅比较物品实际字段，不预估未触发的组合。':'Compare actual item fields; untriggered combinations are not estimated.',
 '右栏详情与比较':'Sidebar details and comparison', '固定／取消固定当前构想':'Pin/unpin the selected conception',
 '返回原条目':'Return to the previous entry', '查看任务相关物品':'View related task items',
 '展开／折叠总览内容':'Expand/collapse overview contents', '固定':'Pinned', '其他':'Other',
 '总览内容已收起；可用上方按钮展开。':'Overview collapsed; use the button above to expand.',
 '固定构想：{n}':'Pinned conceptions: {n}', '可在构想列表中手动固定常用构想。':'Pin frequent conceptions from the Cast list.',
})

EN_UI.update({
 '固定构想／折叠总览':'Pin conception / fold overview', '当前行囊／构想搜索':'Search the current pack or conception list',
 '行囊筛选／排序；征兆页 Alt+L 分类':'Pack filter/sort; Alt+L filters portents',
 '当前物品比较、来源详情或任务物品':'Current item comparison, stat sources, or task items',
 '固定构想；总览中展开或折叠':'Pin a conception; expand or collapse an overview',
 '操作条件已经变化，请重新查看。':'Action conditions changed; review the entry again.',
 '这个征兆已经结束。':'This portent has ended.',
 '剩余 {n} 回合':'{n} turns remaining',
 '展开':'Expand', '日志':'Journal',
 '没有匹配物品；按 Alt+F 修改搜索，或切换分类。':'No matching items; press Alt+F to edit the search, or choose another category.',
 '按键须为单个可打印字符或 Alt+字母／数字／方向键。':'Use one printable character, or Alt plus a letter, digit or arrow key.',
 '面板唤起键必须使用 Alt+字母／数字／方向键。':'Panel shortcuts require Alt plus a letter, digit or arrow key.',
 # —— 2026-10-24 键位治理批次（A1/A2/B5/B10）——
 '面板唤起键；只打开界面，不执行其中操作。':'Panel shortcut: opens the interface only; never performs actions inside it.',
 '右栏子标签：切到当前工作区的上一个子页签（到端停止）。':'Sidebar sub-tab: previous sub-route of the current workspace (stops at the ends).',
 '右栏子标签：切到当前工作区的下一个子页签（到端停止）。':'Sidebar sub-tab: next sub-route of the current workspace (stops at the ends).',
 '右栏光标键：向上选中/滚动；不是地图移动键，地图移动用方向键。':'Right-panel cursor key: move selection up / scroll. Not a movement key — the arrow keys move on the map.',
 '右栏光标键：向下选中/滚动；不是地图移动键，地图移动用方向键。':'Right-panel cursor key: move selection down / scroll. Not a movement key — the arrow keys move on the map.',
 '右栏光标键：向左切子标签；不是地图移动键，地图移动用方向键。':'Right-panel cursor key: previous sub-tab. Not a movement key — the arrow keys move on the map.',
 '右栏光标键：向右切子标签；不是地图移动键，地图移动用方向键。':'Right-panel cursor key: next sub-tab. Not a movement key — the arrow keys move on the map.',
 '进入分层观察后的默认观察层；观察层切换只在本次界面生效，不覆盖本机地图显示偏好。':'Default inspection layer for the layered view; layer switches last for this session only and never overwrite your map display preference.',
 '焦点：地图':'Focus: map',
 '焦点：面板':'Focus: panel',
 '上一个 / 下一个子标签；到端停止（行囊与环境页没有子标签）':'Previous / next sidebar sub-tab; stops at the ends (the Pack and Env pages have no sub-tabs)',
 '焦点跳栏：右栏行最左按 A 回地图；地图焦点按 D 回右栏（/ 循环切换焦点）':'Focus hop: at the leftmost sub-tab press A to return to the map; on the map press D to jump to the panel (/ cycles focus)',
 '观察固定与盘面落点':'Observe pin & board landing policy',
 '物品菜单或详情':'Item menu or details',
 '确认攻击或替换':'Confirm attack or replacement',
 '瞄准切换来源':'Cycle firing sources while aiming',
 '凝听或调试放置':'Listen a turn or debug place',
 '调试面板开关':'Toggle debug panel',
 # —— 2026-10-24 右栏焦点提示与命中跳字（app.py 地图提示条，补英文包缺口）——
 '右栏选择':'Panel',
 '↑↓ 选择 · ←→ 切页':'↑↓ select · ←→ switch pages',
 'Esc 回地图':'Esc returns to the map',
 '地图操作：方向键 移动 · F 发射 · X 观察 · / 右栏':'Map: arrows move · F fire · X observe · / panel',
 '挡':'blocked',
})

# —— 2026-10-24 玩家优化 4 补充：联想盘常驻入口（页签行「盘」按钮）——
EN_UI.update({
    '盘': 'M',
})

# —— 2026-10-24 玩家优化 6：层详情面板（layer_info.py）与层型/修饰符含义 ——
EN_UI.update({
    '当前层': 'Current layer',
    '层名': 'Name',
    '层型': 'Form',
    '修饰符': 'Modifier',
    '修饰符：无——常规层，只有层型本身起作用。': 'Modifier: none — an ordinary layer; only the form itself applies.',
    '点击顶部层信息行 / 任意键 关闭。': 'Click the layer line on top, or press any key, to close.',
    '层信息读取失败。': 'Failed to read the layer info.',
    # 层型含义
    '房间被递归二分成规整的网格，墙体平直、通路端正。': 'Rooms are carved by recursive bisection into a tidy grid: straight walls, orderly passages.',
    '房间的底子上墙缘被啃噬，碎屑与噪点撒满全层。': 'A room floor with gnawed wall edges; debris and static scatter the whole layer.',
    '从一间房向外成片生长的街区，房间彼此贴靠。': 'Blocks grown outward from one seed room, walls pressed wall-to-wall.',
    '天然洞窟，通路由平滑的洞腔连成。': 'Natural caverns; passages wind through smoothed chambers.',
    '窄道蜿蜒的回溯迷宫，几乎每条路都通向别处。': 'A winding backtracker maze of narrow corridors; almost every path leads somewhere else.',
    '一条极长的走廊层，长边约为短边的四倍。': 'One extremely long gallery; the long side is about four times the short one.',
    '重复的房间模块与环形通路，容易迷路。': 'Repeating room modules and looping passages; easy to get lost.',
    '开阔地面上散布着短墙与墙块，视野开阔而掩体稀少。': 'Open ground dotted with short walls and wall blocks; wide sightlines, little cover.',
    '中央大厅配柱列与边室。': 'A central hall flanked by colonnades and side chambers.',
    '一切开始的地方：没有崩解度，随时可以下潜。': 'Where it all begins: no dissolution, and you may descend at any time.',
    '梦的尽头：崩解度在暗中累计，只显示回合数。': 'The end of the dream: dissolution accrues silently; only the turn count is shown.',
    # 修饰符含义
    '本层每条边放大约四分之一，地面更辽阔。': 'Each side of this layer is about a quarter larger; the ground stretches wider.',
    '本层每条边缩短约五分之一，遭遇更密集。': 'Each side of this layer is about a fifth shorter; encounters come thicker.',
    '气体的生成率与存留时间大增，留意吸入效果。': 'Gas spawns far more often and lingers far longer; mind what you breathe.',
    '液体生成率大增，低洼处容易积水。': 'Liquids spawn far more often; lowlands pool easily.',
    '植物覆盖率大增。': 'Plant cover rises sharply.',
    '埋藏的建筑模板更多，稀有模板更常见。': 'More buried architectural templates, and rarer ones appear more often.',
    '特殊与稀有地板的覆盖率大幅提升。': 'Special and rare floor coverage rises sharply.',
})

# 环境页左右分块与构想页两块（2026-10-24 深化批次）。
EN_UI.update({
    '—— 使用预览 ——': '— Usage Preview —',
    '习得构想后，这里显示选中一发的形态与施放流程。':
        'Once you learn constructs, this block shows the selected one\'s form and casting flow.',
    '弹道': 'Projectile', '位移': 'Blink',
    'Enter/左键 进入零消耗瞄准，确认时才支付。':
        'Enter/left-click starts a free aim; you only pay on confirm.',
    'Enter/左键 立即施放。': 'Enter/left-click casts at once.',
    '↑↓ 选择构想 · Enter/左键 施放 · Esc 返回地图':
        '↑↓ choose construct · Enter/left-click cast · Esc back to map',
    '异象': 'Anomalies', '环境概述': 'Survey',
    '（视野 {n} 格）': ' ({n} cells in sight)',
    '总耐久': 'total durability', '总液量': 'total volume', '总气量': 'total gas',
    '株': 'plants', '均值': 'Mean',
    '视野内没有墙体固体。': 'No solid walls in sight.',
    '视觉遮蔽': 'Sight blocked', '遮蔽气/高丛': 'obscuring gas/tall growth',
    '听觉盲区': 'Sound blind spots', '静步': 'silent steps',
    '可燃气': 'flammable gas',
    'Enter 格子详情 · F3/Alt+V 分层观察 · ↑↓ 选择异象':
        'Enter cell detail · F3/Alt+V layers · ↑↓ pick anomaly',
    # 2026-10-24 玩家定稿：键位行移到右栏底部 #panel-help，紧邻完整键位表。
    '↑↓ 选构想 · Enter 施放 · Esc 返回 · 键位表':
        '↑↓ pick construct · Enter cast · Esc back · keys',
    '↑↓ 选来源 · Enter 设为当前 · F 瞄准 · R 换弹 · 键位表':
        '↑↓ pick source · Enter set current · F aim · R reload · keys',
    'Enter 详情 · F3/Alt+V 分层 · ↑↓ 选异象 · 键位表':
        'Enter details · F3/Alt+V layers · ↑↓ anomaly · keys',
})

# —— 2026-10-24 键位定稿：方向键/数字恒移动，WASD 恒控右栏（/ 可交给左浮层）
# （key_routing / app / controls_help）。
EN_UI.update({
    '光标区域：地图（方向键/数字移动；WASD 仍控制右栏）':
        'Cursor area: map (arrows/digits move; WASD still drives the panel)',
    '环境风险': 'Environmental risks',
    'WASD / 滚轮 滚动 · Esc / 点击顶部层信息行 关闭。': 'WASD / wheel: scroll · Esc / click the layer header: close.',
    '接触效果': 'Contact effects',
    '吸入效果': 'Inhalation effects',
    '可燃液体': 'Flammable liquid',
    '地图尺寸': 'Map size',
    '探索进度': 'Exploration',
    '本层停留': 'Time on this layer',
    '视野内': 'In sight',
    '光标区域：右侧面板（WASD 选择切页；方向键/数字移动）':
        'Cursor area: right panel (WASD select and page; arrows/digits move)',
    '光标区域：左侧浮层（WASD 在浮层内选择）':
        'Cursor area: left overlay (WASD selects inside the overlay)',
    '右栏': 'Panel',
    'WASD 选择 · ←→ 切页': 'WASD select · ←→ switch pages',
    '方向键/数字移动 · / 切区域': 'arrows/digits move · / switch area',
    # 右栏焦点提示「Enter 会做什么」（`ui/app/app.py::PANEL_ENTER_HINTS`）。
    # 这些走 `tr(enter)`，漏登时英文模式下右栏提示会夹一句中文。
    'Enter 使用/装备': 'Enter use/equip',
    'Enter 卸下/改装': 'Enter unequip/modify',
    'Enter 查看构筑': 'Enter view build',
    'Enter 查看征兆': 'Enter view omens',
    'Enter 查看自身': 'Enter view self',
    'Enter 查看数值': 'Enter view stats',
    'Enter 查看条目': 'Enter view entry',
    'Enter 执行选中行动': 'Enter run selected action',
    'Enter 查看周围': 'Enter look around',
    'Enter 查看任务': 'Enter view tasks',
    'Enter 继续': 'Enter continue',
    'Enter 执行选中项': 'Enter run selection',
    '地图：方向键 / 数字 移动 · WASD 右栏 · / 切区域':
        'Map: arrows / digits move · WASD panel · / switch area',
    '左栏：WASD 在浮层内选择 · / 切区域':
        'Left overlay: WASD selects inside it · / switch area',
    '移动角色（始终，与区域无关）；小键盘 5 等待可在设置中关闭':
        'Move the player (always, regardless of area); keypad 5 wait can be disabled in settings',
    '恒控右栏：W/S 选择 · A/D 切页；左浮层开着时按 / 把 WASD 交给浮层':
        'Always drives the panel: W/S select · A/D switch pages; with a left overlay open, / hands WASD to it',
    '切换 WASD 的区域：地图 / 右栏都控右栏，左浮层开着可切给浮层（永不控地图）':
        'Switch the WASD area: map and panel both drive the panel; with a left overlay open it can take WASD (never the map)',
    '梦层的边角又渗出一道轮廓——{name}在远处成形。':
        'A shape seeps out at the edge of the dream — {name} forms in the distance.',
    '{name}的碎片落进梦里——崩解度 +1。':
        'Fragments of {name} fall into the dream — dissolution +1.',
    '你把它推得嵌进阻碍里——{name}碎开了。':
        'You shove it hard into the obstruction — {name} breaks apart.',
    '周围区域噪音：{n}/20（最近 {turns} 回合）':
        'Ambient noise: {n}/20 (last {turns} turns)',
    '来自你周围区域的真实声音，来源不一定是自己。':
        'Real sound around your area — not necessarily from you.',
    '{where}的尾音分辨出来了：{verdict}。':
        'The tail of {where} resolves: {verdict}.',
    '声音的方位或远近在两声之间变了，那是移动中的东西':
        'The bearing or distance shifted between the two sounds — something is moving',
    '两声的方位与远近都一样，那是固定节律的声响，不是走过来的脚步':
        'Both sounds share bearing and distance — a fixed rhythm, not footsteps approaching',
    '借外部灯的亮光，{n} 格地形轮廓记进了记忆。':
        'Borrowed lamplight: {n} terrain outlines written to memory.',
    '那个方向': 'that direction',
    '那处声响': 'that sound',
    '静音折线落在 ({x}, {y})：跨过这两段缝的声音都少一格余量，视线照旧。':
        'Quiet fold at ({x}, {y}): sound crossing either seam loses one unit of headroom; sight is untouched.',
    '积水的年龄：({x}, {y}) 的液体正在{change}。':
        'Age of the standing water: the liquid at ({x}, {y}) is {change}.',
    '积聚': 'gathering',
    '消退': 'ebbing',
    '阴影会移动：({x}, {y}) 的遮挡轮廓与上次亲见不同。':
        'Shadows move: the occlusion at ({x}, {y}) differs from the last time you saw it.',
    '不追最后一声：{name}上次确认的调查目标是 ({x}, {y})。':
        'No chasing the last sound: {name} last confirmed an investigation target at ({x}, {y}).',
    '你已经习得这个构想。': 'You have already learned this construct.',
    '你已经拥有这个洞察。': 'You already have this insight.',
    '请先安置或放弃待选的洞察。': 'Place or dismiss the pending insight first.',
    '请先安置或放弃待选的记忆。': 'Place or dismiss the pending memory first.',
    '事件线索兑现：{name}。': 'Event clue pays off: {name}.',
    '这次奖励机会已经结束。': 'This reward opportunity has ended.',
    '这个目标不在当前线索中。': 'That target is not among the current clues.',
    '请选择要追寻的目标。': 'Choose which target to pursue.',
    '这个目标目前不能获得。': 'That target cannot be obtained right now.',
    '{name}：{description}': '{name}: {description}',
    '返回原事件': 'Back to the event',
    '这个条目不是成长内容。': 'That entry is not growth content.',
    '追寻{clue}（与原奖励择一）': 'Pursue {clue} (in place of the original reward)',
    '这件显化物只能从指定来源获得。': 'This manifested item can only come from its designated source.',
    '合唱里有一条 {gap} 回合的间隙：先 {a}，后 {b}。两条声线分开记着，不并成一处。':
        'A gap of {gap} turns splits the chorus: first {a}, then {b}. '
        'Two separate sound lines, never merged into one place.',
    '记住的反折面：({x}, {y}) 脚下的材料换了，那条反射记录作废。':
        'Remembered reflecting face: the material under ({x}, {y}) changed, '
        'so that bounce note is out of date.',
    '记住的反折面：本回合核对了 {n} 处亲眼所见的反射面。':
        'Remembered reflecting face: {n} firsthand surfaces checked this turn.',
    '认光源而非亮斑：{n} 格是它自己在发光——{cells}，半径 {r}。':
        'Read the source, not the bright spot: {n} cells glow by themselves — '
        '{cells}, radius {r}.',
    '认光源而非亮斑：{n} 格的亮借自眼前确认过的灯——{cells} 归 ({sx}, {sy})。':
        'Read the source, not the bright spot: {n} cells borrow their light from a '
        'lamp already in view — {cells} belong to ({sx}, {sy}).',
    '认光源而非亮斑：{n} 格的亮换了来处——{cells} 现在归 ({sx}, {sy}) 那盏灯。':
        'Read the source, not the bright spot: {n} cells changed light source — '
        '{cells} now come from the lamp at ({sx}, {sy}).',
    '认光源而非亮斑：{n} 格亮着，可眼前没有一盏确认过的灯解释得了它们——{cells}；不据此猜灯在哪。':
        'Read the source, not the bright spot: {n} cells are lit, yet no lamp in view '
        'accounts for them — {cells}; that is not a hint about where a lamp hides.',
    '认光源而非亮斑：{n} 格此刻说不清来处，最近一次确认的仍是 ({sx}, {sy}) 那盏灯。':
        'Read the source, not the bright spot: {n} cells have no source they can show '
        'right now; the last one confirmed was the lamp at ({sx}, {sy}).',
    '先断哪根：断「{line}」落不到任何接收端——那根线不牵着机关。':
        'Which wire to cut first: severing “{line}” reaches no receiver — '
        'that line is not holding any mechanism.',
    '先断哪根：断「{line}」会落到 {receivers}。':
        'Which wire to cut first: severing “{line}” falls on {receivers}.',
    '先断哪根：「{line}」眼下不带电，断了不改变什么——它牵着 {receivers}。':
        'Which wire to cut first: “{line}” carries no current right now, so cutting '
        'it changes nothing — it runs to {receivers}.',
    '先断哪根：另有 {n} 根已见线路的落点一并记下。':
        'Which wire to cut first: {n} more seen lines noted as well.',
    '先断哪根：「{line}」的落点和上次确认不一样了——现在牵着 {receivers}。':
        'Which wire to cut first: “{line}” no longer lands where it was last '
        'confirmed — it now runs to {receivers}.',
    '先断哪根：{n} 根线牵着没看清的接收端——只说可能有未明连线，不给坐标。':
        'Which wire to cut first: {n} lines run to receivers still unseen — '
        'possible uncharted links are noted, never coordinates.',
    '蒸气的出口：本回合 {n} 格新起了气——{cells}，自 ({sx}, {sy}) 推进。':
        'Where the steam escapes: {n} cells caught vapor this turn — {cells}, '
        'pushed in from ({sx}, {sy}).',
    '蒸气的出口：另有 {n} 格新推进的落点一并记下。':
        'Where the steam escapes: {n} more cells the front reached are noted as well.',
    '蒸气的出口：本回合 {n} 格起了气，可上一回合没看见挨着它的气——{cells}；不猜来向。':
        'Where the steam escapes: {n} cells caught vapor, yet no gas beside them was '
        'seen last turn — {cells}; the direction is not guessed.',
    '蒸气的出口：本回合 {n} 格的气退了——{cells}。':
        'Where the steam escapes: {n} cells lost their vapor this turn — {cells}.',
    '留意熄灯顺序：({ax}, {ay}) 先于 ({bx}, {by}) 熄灭，两次亲见分别隔 {g1}、{g2} 回合。':
        'Watch the lights out: ({ax}, {ay}) went dark before ({bx}, {by}); the two witnessed gaps were {g1} and {g2} turns.',
    '留意熄灯顺序：这一对的上游是亲眼见过的「{label}」 ({x}, {y})。':
        'Watch the lights out: upstream of this pair is “{label}” at ({x}, {y}), seen with your own eyes.',
    '留意熄灯顺序：这一对的控制端两次都没看见，按未知记下。':
        'Watch the lights out: neither control end was seen for this pair — noted as unknown.',
    '留意熄灯顺序：另有 {n} 对已确认的先后一并记下。':
        'Watch the lights out: {n} more confirmed orders are noted as well.',
    '留意熄灯顺序：({ax}, {ay}) 与 ({bx}, {by}) 两次的先后相反，这条推演作废。':
        'Watch the lights out: ({ax}, {ay}) and ({bx}, {by}) came out in the opposite order the two times — this deduction is void.',
    '留意熄灯顺序：{n} 对灯在同一回合熄灭，分不出先后——{pairs}。':
        'Watch the lights out: {n} pairs of lamps went dark in the same turn, so no order can be told — {pairs}.',
    '亮处未必安全：({x}, {y}) 的「{label}」站在亮区里，它此刻正看得见你（视距 {v}）。':
        'Bright places aren’t always safe: “{label}” at ({x}, {y}) stands in a lit area and can see you right now (vision {v}).',
    '亮处未必安全：({x}, {y}) 的「{label}」站在亮区里，眼下隔着遮挡，但你已经在它视距 {v} 之内。':
        'Bright places aren’t always safe: “{label}” at ({x}, {y}) stands in a lit area; the line is blocked for now, but you are already within its vision {v}.',
    '亮处未必安全：另有 {n} 个亮区里已确认的视觉型异象一并记下。':
        'Bright places aren’t always safe: {n} more confirmed visual anomalies standing in light are noted as well.',
    '同拍才接：另有 {n} 对可提交端口一并记下。':
        'Same-turn pairing: {n} more pairs of submittable ports are noted as well.',
    '同拍才接：另有 {n} 对读数改口一并记下。':
        'Same-turn pairing: {n} more pairs whose reading changed are noted as well.',
    '同拍才接：「{left}」与「{right}」只过不带记忆的接线，落在「{recv}」时同一回合到。':
        'Same-turn pairing: “{left}” and “{right}” run only through wiring that remembers nothing, so they arrive at “{recv}” in the same turn.',
    '同拍才接：「{left}」与「{right}」眼下不同拍——中间那只「{el}」记得住上一回合。':
        'Same-turn pairing: “{left}” and “{right}” are not on the same beat — “{el}” in between remembers the previous turn.',
    '同拍才接：「{left}」与「{right}」的下级接得太密，这一眼读不完——未明的延迟标未知。':
        'Same-turn pairing: “{left}” and “{right}” fan out too densely to read in one glance — the delay is marked unknown.',
    '同拍才接：「{left}」与「{right}」之间有一截接线没看清——未明的延迟标未知，不猜第几回合到。':
        'Same-turn pairing: a stretch of wiring between “{left}” and “{right}” was never seen — the delay is marked unknown instead of guessing which turn it lands on.',
    '看见回流：({x}, {y}) 的出口在退——这一格少了 {n} 单位{medium}，不像是管子往它那边送的样子。原因还得自己再看一眼。':
        'Spot the Backflow: the outlet at ({x}, {y}) is receding — this tile lost {n} units of {medium}, which is not how a tube feeds it. Look again before naming a cause.',
    '看见回流：({x}, {y}) 的出口没退，倒是 ({sx}, {sy}) 的源多回来 {n} 单位{medium}——这一眼只报方向反了。原因还得自己再看一眼。':
        'Spot the Backflow: the outlet at ({x}, {y}) held, but the source at ({sx}, {sy}) took back {n} units of {medium} — this glance only reports that the direction reversed. Look again before naming a cause.',
    '看见回流：({x}, {y}) 的出口退了 {o} 单位{medium}，({sx}, {sy}) 的源反倒多回 {s} 单位——两头都在倒着走。原因还得自己再看一眼。':
        'Spot the Backflow: the outlet at ({x}, {y}) gave back {o} units of {medium} while the source at ({sx}, {sy}) took back {s} — both ends running the wrong way. Look again before naming a cause.',
    '看见回流：另有 {n} 处已见出口的逆流一并记下。':
        'Spot the Backflow: {n} more changed visible outlets are noted as well.',
    '看见回流：重新看到 ({x}, {y}) 的出口——读数从 {was} 变成 {now}。这一眼仍只报数，不替它说原因。':
        'Spot the Backflow: looked at the outlet at ({x}, {y}) again — the reading went from {was} to {now}. This glance still only reports numbers, not a cause.',
    '看见回流：另有 {n} 处重新看到的出口读数一并记下。':
        'Spot the Backflow: {n} more re-read outlets are noted as well.',
    '看见回流：{n} 处报过的逆流还没重新看到出口的新读数——不替它们猜原因。':
        'Spot the Backflow: {n} reported backflows have not been seen again with a new outlet reading — no cause is guessed for them.',
    '沿这一向我确认过的地形只到 {n} 格，再往外是没亲自走过的地方。它不报边界之外有什么。':
        'Along this bearing my confirmed ground reaches only {n} tiles; past it is ground I have not walked myself. It says nothing about what lies past the edge.',
    '边界更深：({x}, {y}) 的出口在{bearing}、约 {distance} 格外——{tail}':
        'The Boundary Runs Deeper: the exit at ({x}, {y}) lies to the {bearing}, about {distance} tiles off — {tail}',
    '这一向我连一格确认过的地形都没有，边界在哪说不清。':
        'Along this bearing I have not confirmed a single tile of ground, so I cannot say where the edge is.',
    '出口还在已确认的地形里，走得过去。':
        'The exit is still inside confirmed ground — walkable.',
    '边界更深：另有 {n} 处看得见的出口一并记下。':
        'The Boundary Runs Deeper: {n} more visible exits are noted as well.',
    '边界更深：重新对上 ({x}, {y}) 的出口——现在在{bearing}、约 {distance} 格外，{tail}':
        'The Boundary Runs Deeper: the exit at ({x}, {y}) lines up again — now to the {bearing}, about {distance} tiles off, {tail}',
    '边界更深：另有 {n} 处出口改了读数一并记下。':
        'The Boundary Runs Deeper: {n} more exits with changed readings are noted as well.',
    '留给对方一拍：({x}, {y}) 的「{label}」这一招「{skill}」连听两回蓄势，两次起手之间隔了 {gap} 回合。它不预测下一回收在哪里。':
        'Leave It a Beat: the rhythm of "{skill}" from "{label}" at ({x}, {y}) -- two wind-ups I heard, {gap} turns between the starts. It does not predict where the next one lands.',
    '留给对方一拍：另有 {n} 条节拍读数一并记下。':
        'Leave It a Beat: {n} more rhythm readings are noted as well.',
    '留给对方一拍：「{label}」换了要蓄势的那一招——先前「{skill}」那条节拍不作数了。':
        'Leave It a Beat: "{label}" switched which move it is winding up -- the rhythm I had for "{skill}" no longer counts.',
    '留给对方一拍：另有 {n} 条作废一并记下。':
        'Leave It a Beat: {n} more voided rhythms are noted as well.',
})

# ---- 光与土构想第二批（2026-10-25）：借昼 / 逐格熄灯 / 犁沟 / 抬沿 ----
EN_UI.update({
    "那不是一盏灯。": "That is not a lamp.",
    "那盏灯不在你能碰的地方。": "That lamp is not somewhere you can reach.",
    "那一格没有亮着的灯。": "No lamp on that tile is burning.",
    "那盏灯已经暗到借不出光。": "That lamp is too dim to lend any light.",
    "你脚下本来就比那盏灯亮。": "The ground you stand on is already brighter than that lamp.",
    "你从 ({x}, {y}) 那盏灯借了三回合光：脚下亮起来，那盏灯暗了一档。":
        "You borrow three turns of light from the lamp at ({x}, {y}): your footing lights up and that lamp drops a step.",
    "可见范围里没有你能碰的灯。": "No lamp you can work is in sight.",
    "你记下 {n} 盏灯：接下来每回合熄一盏，机关灯不在此列。":
        "You mark {n} lamps: one goes dark each turn, and locked mechanism lamps are not among them.",
    "这条沟要三格都看得见，且都不在保护面上。":
        "The furrow needs all three tiles in sight and none of them on a protected surface.",
    "那一段已经到底了。": "That stretch is already at the bottom.",
    "挖出来的土没地方放——两侧都接不下这一档。":
        "The dug soil has nowhere to go: neither side can take that step.",
    "你在这一段犁出三格沟，挖出的 {n} 档土堆到两侧。":
        "You plough a three-tile furrow there and pile the {n} steps of soil on either side.",
    "你脚下这一格没有可以取土的邻格。": "The tile you stand on has no neighbour to take soil from.",
    "你脚下这一格不能挖。": "You cannot dig the tile you are standing on.",
    "取土和落沿的两格都得看得见、且不在保护面上。":
        "Both the soil source and the rim tile must be in sight and off protected surfaces.",
    "那一格已经是最高的低沿了。": "That tile is already the highest a low rim goes.",
    "取土那一格已经到底了。": "The soil source is already at the bottom.",
    "你从 ({sx}, {sy}) 取了一档土，把 ({x}, {y}) 抬成一道低沿。":
        "You take a step of soil from ({sx}, {sy}) and raise ({x}, {y}) into a low rim.",
})

# ---- 电路与边界构想第三批（2026-10-25）：短接 / 析出 / 复核脉冲 / 边界回折 ----
EN_UI.update({
    "那一格上没有可以短接的端口。": "There is no port on that tile to jumper.",
    "那是设施自己的接线，不归你改。": "That wiring belongs to the facility; it is not yours to change.",
    "你把 ({x}, {y}) 那个端口短接了三回合：这段时间它一直是通的。":
        "You jumper the port at ({x}, {y}) hot for three turns: it reads as live the whole time.",
    "那一格里没有能接出来的东西。": "There is nothing in that tile to draw out.",
    "你手上没有能接住它的空容器。": "You are not carrying an empty container to catch it.",
    "容器里已经装了别的东西。": "The container already holds something else.",
    "容器已经满了。": "The container is already full.",
    "接不出来了——这一格里的东西不归你动。": "It will not draw out: what is in that tile is not yours to move.",
    "你把 ({x}, {y}) 里的一组分接进 {item}，反应不会被倒着走。":
        "You draw a component out of ({x}, {y}) into {item}; no reaction runs backwards for it.",
    "本层还没有你自己发出的信号可复核。": "You have sent no signal of your own on this layer to recheck.",
    "那个端口已经不在了。": "That port is no longer there.",
    "那处端口不是能复送的脉冲。": "That port is not a pulse you can resend.",
    "你把 ({x}, {y}) 那一次脉冲又送了一遍：机关自己的次数限制没有回到起点。":
        "You send the pulse at ({x}, {y}) again: the mechanism's own count does not go back to the start.",
    "两头得隔开一点：太近了不用折，太远了折不过去。":
        "The two ends need some distance: too close and there is nothing to fold, too far and it will not fold.",
    "两头都得是空位。": "Both ends have to be empty ground.",
    "那一头你还没亲自走到过。": "You have not walked to that end yourself yet.",
    "那一头压在机关面上——折不通。": "That end sits on a mechanism surface: the fold will not take.",
    "你把边界折了一道：({ax}, {ay}) 与 ({bx}, {by}) 之间只隔一步。":
        "You fold the boundary once: ({ax}, {ay}) and ({bx}, {by}) are now a single step apart.",
})

# ---- 构想第四批（2026-10-25）：开气窗 / 压膛 / 退壳 / 排线 / 迟发 / 缓拍 / 封炉 / 冷铸 / 代为护理 ----
EN_UI.update({
    "那一格不是已经有的开口。": "That tile is not an opening that already exists.",
    "那是保护面——气窗不开在保护墙上。": "That is a protected surface: vents do not go into protected walls.",
    "这一段已经开过气窗了。": "A vent is already open on this stretch.",
    "你在 ({x}, {y}) 开了个气窗：这一段的气会散得更快，{n} 回合后自己合上。":
        "You open a vent at ({x}, {y}): gas here clears faster, and it closes by itself in {n} turns.",
    "弹匣是空的——压不了膛。": "The magazine is empty; nothing to press in.",
    "上一发还压在里面没打出去。": "The last round is still pressed in and unfired.",
    "你多压了一发：下一发打出去会多穿 {n} 档。":
        "You press in an extra round: the next shot pierces {n} more steps.",
    "手上没有能打空的弹匣。": "You are not holding a magazine you can empty.",
    "你把弹匣里剩下的 {n} 发一次打空，地上落了一层壳。":
        "You empty the remaining {n} rounds at once; a layer of casings drops.",
    "你脚下这一格没有方向可量。": "There is no bearing to measure from the tile you stand on.",
    "这一向上没有看得见的格子。": "No tile along that bearing is in sight.",
    "你沿这一向把弹道排出来：{n} 格记进了记忆，一枪没开。":
        "You lay the trajectory out along that bearing: {n} tiles go into memory, not a shot fired.",
    "没有可以压进膛的弹。": "There is no round to press in.",
    "你先把这一发压在那里：({x}, {y}) 会在 {n} 回合后响一枪，那里没有人。":
        "You press the round in place: ({x}, {y}) will crack one shot in {n} turns, and nobody is there.",
    "那一格上没有端口。": "There is no port on that tile.",
    "那处端口不是能缓一缓的脉冲。": "That port is not a pulse you can slow down.",
    "那处端口上没有还没走完的信号。": "No signal is still running at that port.",
    "你把 ({x}, {y}) 那一次信号压慢了一拍，它多留了一回合。":
        "You slow the signal at ({x}, {y}) by a beat; it lingers one more turn.",
    "那一格上没有能临时封住的破口容器。":
        "There is no cracked vessel on that tile to seal for now.",
    "那一格里的东西凝不住——要么没有液体，要么已经在凝了。":
        "What is on that tile will not set: either there is no liquid, or it is already setting.",
    "你把 ({x}, {y}) 里的 {n} 单位就地凝住了，那块地方现在走不过人。":
        "You set the {n} units at ({x}, {y}) where they stand; nobody walks through that spot now.",
    "那一格上不是能接受护理的人。": "There is nobody on that tile who can take the care.",
    "得挨着才施得了手。": "You have to be right beside them to do this.",
    "你身上没有可以递过去的恢复品。": "You are carrying nothing restorative to hand over.",
    "你把 {item} 递给了 {name}：恢复算在它身上，账还记在你名下。":
        "You hand {item} to {name}: the recovery counts for them, the debt stays in your name.",
})

# ---- 洞察 A 批（2026-10-25）：墙后的空腔／反应留下出口／药效不等于痊愈 ----
EN_UI.update({
    "墙后的空腔：({x}, {y}) 后面的回声{band}——{shape}。里面有什么、怎么进去，这一手听不出来。":
        "Hollow in the wall: the echo behind ({x}, {y}) is {band} — {shape}. "
        "What is inside and how to get there is not something this knock can tell.",
    "很短": "very short",
    "偏短": "short",
    "偏长": "on the long side",
    "很长": "very long",
    "墙后立刻又是实的": "the wall is solid again right behind it",
    "墙后只有一线空处": "there is only a sliver of space behind it",
    "墙后是一片不大的空处": "it opens into a small pocket of space",
    "墙后连着更大的空处": "it opens into a larger hollow",
    "反应留下出口：把{item}倒进 ({x}, {y}) 会生成{product}——"
    "这是已知会产气的最近一格；没见过的通路不能当安全。":
        "A reaction leaves an exit: pouring {item} onto ({x}, {y}) produces {product} — "
        "the nearest tile known to give off gas. A route you have not seen is not a safe one.",
    "药效不等于痊愈：你把「{item}」的一格账提前结了——{resource} −1，还剩 {n} 格；"
    "总债没有变少，也没有提前恢复什么。":
        "Medicine is not recovery: you settle one instalment of “{item}” early — "
        "{resource} −1, {n} instalments left. The total debt is no smaller, and nothing healed early.",
})

# ---- 洞察 B 批（2026-10-25）：数清空响／光圈的边缘 ----
EN_UI.update({
    "数清空响：{name} 这一仓是你自己打空的——下一次换弹的第一步会快一点，"
    "该付的费用一分不少。":
        "Counting the empty clicks: you emptied {name} yourself — the first step of its next "
        "reload goes a little faster, and the usual cost is still paid in full.",
    "光圈的边缘：你在明暗交界停了一手——下一步跨进暗处，露光少一格；"
    "踏进别的真实光源就作废。":
        "The edge of the lit circle: you paused on the light-dark boundary — the next step into "
        "the dark shows one tile less of you. Stepping into any other real light voids it.",
})

# ---- 洞察 C 批（2026-10-25）：先让它沉下去 ----
EN_UI.update({
    "先让它沉下去：({x}, {y}) 刚相变完，这时候取液沾不上表面附着——"
    "身上的东西该发作还是发作。":
        "Let it settle first: ({x}, {y}) has just changed phase — taking liquid now leaves no "
        "surface residue on you, though whatever you already carry still acts as it would.",
    "先让它沉下去：这一格刚相变完，表面附着没有跟上你——"
    "身上的东西该发作还是发作。":
        "Let it settle first: this tile only just changed phase, so the surface residue does not "
        "latch onto you — whatever you already carry still acts as it would.",
})

# ---- 洞察 D 批（2026-10-25）：落笔之前 ----
EN_UI.update({
    "落笔之前：你把 ({x}, {y}) 那发朝向{old}的构想转到{new}——"
    "落点、范围与剩下的 {n} 回合一个数都不动。":
        "Before the pen touches: you turn the pending construct at ({x}, {y}) from {old} to "
        "{new} — the landing tile, the reach and the {n} turns still on the clock all stay put.",
})

# ---- 洞察 E 批（2026-10-25）：先看落差／不把亮灯当通电／一声两种来处 ----
EN_UI.update({
    "先看落差：脚下的地势比 {where} 高——从这里倒液会先往那边走，"
    "这一份可以分两段确认。":
        "Mind the drop first: the ground under you is higher than {where} — liquid poured here "
        "will run that way first, so this measure can be confirmed in two stages.",
    "先看落差：这一手只走了一半，剩下的还在容器里——"
    "看过这一段的反应，再倒一次才倒完。":
        "Mind the drop first: this pour only went half way — the rest is still in the container. "
        "Watch what this part does, then pour again to finish.",
    "不把亮灯当通电：附近那条线亮着，不等于通着电——你身上还有 {n} 层积电；"
    "贴着一个端口断开、验过电再接线，能泄掉一层，灯灭不算断电。":
        "A lit wire is not a live check: the line nearby glows, but glowing is not being live — "
        "you still carry {n} layers of charge. Break the line at a port you can reach, verify it, "
        "and rewiring sheds one layer; a dark lamp is not the power being off.",
    "不把亮灯当通电：你就着这条线断了电、验了一下——身上泄掉一层积电，"
    "灯亮不亮都不算断电。":
        "A lit wire is not a live check: you broke the line here and verified it — one layer of "
        "charge bleeds off you. Whether the lamp glows says nothing about the power.",
    "一声两种来处：这一声是经传声筒从 ({x}, {y}) 转过来的——"
    "原声在那一头，不在这边。":
        "One sound, two places: this one was relayed through the speaking tubes from ({x}, {y}) — "
        "the original sound is at that end, not here.",
    "一声两种来处：这一声是传声筒转过来的，入口 ({x}, {y}) 你没亲眼见过——"
    "另一头不替你追。":
        "One sound, two places: this one came through the speaking tubes, and you have not seen "
        "the mouth at ({x}, {y}) yourself — the other end is not traced for you.",
    "经传声筒转发，入口：({x},{y})": "relayed through the speaking tubes, mouth: ({x},{y})",
    "经传声筒转发（入口未见）": "relayed through the speaking tubes (mouth unseen)",
})

# ---- 洞察 F 批（2026-10-25）：桌面不是地面／听出填装间隙／留下最后一条路 ----
EN_UI.update({
    "桌面不是地面：你多站了一回合，慢慢把东西取下来——"
    "陷阱没踩响，石台照旧发了信号。":
        "A table is not the floor: you stood one extra turn and lifted the thing off slowly — "
        "the trap never fired, and the slab still sent its signal.",
    "桌面不是地面：{where} 底下有机关——多站一回合慢慢取，陷阱就不响；"
    "石台照旧发信号，机关石台也照旧触发。":
        "A table is not the floor: there is a mechanism under {where} — stand one extra turn and "
        "take it slowly, and the trap stays quiet; the slab still signals, and trigger slabs "
        "still trigger.",
    "听出填装间隙：{name} 还差 {n} 步装填——这一步的声音大约传到 {step} 格，"
    "最后那一步更响（{done} 格）。":
        "Hearing the reloading gap: {name} is {n} step(s) short — that step carries about "
        "{step} tiles, and the last one is louder ({done} tiles).",
    "留下最后一条路：{where} 一堵上，你已经知道的那片就断了——"
    "没见过的通路不能当退路。":
        "Keep one route open: block {where} and the part you already know is cut off — a route "
        "you have never seen is not a way back.",
})

# ---- 洞察 G 批（2026-10-25）：先看掩体边／不白退一发／空仓不是失手 ----
EN_UI.update({
    "先看掩体边：这面掩体两侧都被堵着——要换个出手的位置，得先挪身。":
        "Mind the edge of cover: both sides of this cover are blocked — a different firing "
        "position means moving first.",
    "先看掩体边：{where} 能从掩体旁边出手，人不用挪；"
    "越过掩体的弹道还是按老规矩算。":
        "Mind the edge of cover: {where} lets you shoot from beside the cover without moving; "
        "any path over the cover is still traced the usual way.",
    "不白退一发：{name} 膛里还有 {n} 发——退壳会打掉 {fired} 发，"
    "最后那一发留在膛里，随时能打出去。":
        "Not a wasted round: {name} still has {n} in the magazine — dumping it fires {fired} "
        "and keeps the last one chambered, ready to go.",
    "不白退一发：{name} 膛里只剩 {n} 发——退壳就真打空了，留不下东西。":
        "Not a wasted round: {name} is down to {n} — dumping it really does empty the magazine, "
        "with nothing kept back.",
    "空仓不是失手：{name} 看见你枪口空着，你就势慢条斯理地做出一次装填——"
    "机括响在自己脚下，看它敢不敢顺着这声音过来。":
        "An empty magazine is not a miss: {name} saw your muzzle run dry, so you take your time "
        "through a fake reload — the mechanism clicks at your own feet; let it dare to come to "
        "that sound.",
    "你把弹匣里剩下的 {n} 发一次打空，地上落了一层壳——"
    "最后那一发留在膛里，随时能打出去。":
        "You dump the remaining {n} rounds at once and a layer of casings hits the floor — the "
        "last one stays chambered, ready to fire.",
    "假装填": "Fake Reload",
    "留意产物：({x}, {y}) 这一格在走你见过的那条反应——{kind}与{gas}出的是{product}，"
    "没见过的组合不替你反演。":
        "Watching the product: ({x}, {y}) is running a reaction you have seen before — {kind} "
        "and {gas} give {product}. A combination you have never seen is not worked out for you.",
    "熔断前的气味：脚下这块压电地板已经蓄了 {n} 层，再有 {left} 层就要放电——"
    "这只报你踩着的那一格，墙后的线路它闻不出来。":
        "The smell before the fuse blows: this piezoelectric floor underfoot holds {n} layers, "
        "{left} more and it discharges. It reports only the tile you stand on; wiring behind "
        "walls gives off no smell.",
    "看完再签：{name} 桌上的这一笔要抽走 {what}——按下之前都还能退，"
    "付不出就不会成交。":
        "Read before signing: this offer on {name}'s table takes {what} — you can still back out "
        "before choosing, and an offer you cannot pay for will not close.",
    "{item} ×{n}（行囊里有 {owned}）": "{item} ×{n} ({owned} in the pack)",
    "摄入物/易逝物 ×{n}（行囊里有 {owned}）":
        "food or perishables ×{n} ({owned} in the pack)",
    "可支付的携带意象 ×{n}（行囊里有 {owned}）":
        "payable carried images ×{n} ({owned} in the pack)",
    "页码没有走动：({x}, {y}) 这一页就是这一刻记下的——"
    "它和你眼前看到的是同一段走廊。":
        "The page has not turned: ({x}, {y}) was written down at this very moment — it is the "
        "same corridor you are looking at.",
    "页码没有走动：({x}, {y}) 这一页还是 {age} 回合前记下的，"
    "中间没再翻过——旧页当不了同一段走廊的凭据。":
        "The page has not turned: ({x}, {y}) was last written {age} turn(s) ago and has not been "
        "turned since — a stale page is no evidence of the same corridor.",
})
