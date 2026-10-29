"""Equipment reading and punctuation UI translations."""
EN_EQUIPMENT = {
    '目标：正交相邻的受损墙体；成功消耗一件工具。':'Target: a damaged wall one cardinal step away; success consumes one tool.',
    '目标：可见可达的格子；读取最短路径，成功消耗一件卷尺。':'Target: a visible reachable cell; measure the shortest route and consume one tape measure.',
    '工具语句的目标或来源不满足条件。':'The tool clause has no valid target or source.',
    '消耗 1 件工具 · 耗时 1 回合 · 距离 {range}':'One tool · 1 turn · range {range}',
    '再':'again',
    '再需要位于所追加的行为之前':'Again must precede the behavior it repeats.',
    '再需要一个可追加的真实行为':'Again needs a real supported repeatable behavior.',
    '再需要唯一且明确的后续行为':'Again needs one unambiguous following behavior.',
    '这个行为的有界追加执行尚未接入':'Bounded repetition for this behavior is not implemented yet.',
    '追加已停止：资源或落点已改变。':'Repetition stopped: resources or the destination changed.',
    '前一次真实发生后至多追加一次，重查资源并共享根预算。':'Add at most one repeat after the first actually happens; recheck resources and share the root budget.',
    '事件条件需要可执行的响应，不能暂时启用持续契约': 'An event condition needs an executable response, not a temporary passive contract.',
    '条件分句包含旧标点或旧行为填充词': 'The conditional clause contains legacy punctuation or a legacy verb filler.',
    '如果不能跨越另一个功能词寻找条件': 'The word if cannot skip another grammar word to find its condition.',
    '如果': 'if', '否则': 'otherwise',
    '条件分句缺少合法行为': 'The conditional clause has no valid behavior.',
    '条件分句存在多个不明确的行为': 'The conditional clause has ambiguous behaviors.',
    '如果需要位于条件之前': 'If must precede its condition.',
    '如果缺少真实条件': 'If needs a real condition.',
    '如果之后的装备没有条件词义': 'The item after if has no condition meaning.',
    '否则缺少唯一相邻的如果分句': 'Otherwise needs one adjacent if clause.',
    '否则需要位于如果分句之后': 'Otherwise must follow the if clause.',
    '否则需要位于反分句之前': 'Otherwise must precede its clause.',
    '此成分已归于条件分句': 'This constituent belongs to the conditional clause.',
    '想象力不超过 {n}': 'imagination is at most {n}', '想象力已耗尽': 'imagination is depleted',
    '目标已有征兆': 'the target has a portent', '落点可导电': 'the target cell conducts electricity',
    '发生 {event}': 'on {event}', '条件不可判定': 'condition unknown',
    '如果 {condition} → 第 {n} 行': 'if {condition} → row {n}',
    '真实条件满足时才求值所绑定分句；本词不提供条件。': 'Evaluate the bound clause only when its actual condition holds. The word supplies no condition.',
    '只在对应如果条件为假时求值，缺资源不等于条件为假。': 'Evaluate only when the paired if condition is false. Missing resources do not mean a false condition.',
    '或者': 'or', '本次语句': 'This action sentence',
    '或者需要左右各有一个候选成分': 'An alternative needs a candidate on each side.',
    '候选成分存在歧义': 'The alternative constituents are ambiguous.',
    '候选成分没有可执行的主动行为': 'Neither candidate has an executable active behavior.',
    '本次只采用一个合法分支，不同时领取两边效果。': 'Use one valid branch for this action, never both effects together.',
    '请选择本次动作的分支': 'Choose a branch for this action.',
    '↑↓ 选择 · Enter/左键 执行 · 数字直选 · Esc/Q 取消（不耗时）': 'Up/Down select · Enter/click execute · Number selects · Esc/Q cancel (free)',
    '和': 'and',
    '并列需要左右各有一个合法成分': 'Coordination needs a valid constituent on each side.',
    '并列成分存在歧义': 'The coordinated constituents are ambiguous.',
    '并列成分没有合法行为': 'A coordinated constituent has no valid action.',
    '并列行为类型不相容': 'These behaviors cannot share a coordinated action.',
    '并列两个相容成分或分句，共用一次根动作与资源预算。': 'Coordinate compatible constituents, sharing one root action and resource budget.',
    '的': 'of', '地': 'manner', '把': 'direct object', '轻快': 'Swift',
    '功能词 z': 'Grammar word z', '关系成立': 'Relation formed',
    '功能词只允许横向摆放。': 'Grammar words must stay horizontal.',
    '盘中已有这个功能词，请移动原词块。': 'This word is already on the board. Move the existing token.',
    '多个功能词需要明确的组合关系': 'Multiple words need an explicit compound relationship.',
    '此功能词的关系求值尚未接入': 'This grammatical relationship is not available yet.',
    '只需要位于所限定的行为之前': 'Only must precede the restricted action.',
    '只缺少后续行为': 'Only needs a following action.',
    '只的行为存在歧义': 'The action restricted by only is ambiguous.',
    '只需要一个明确的主动行为': 'Only needs one explicit active action.',
    '此成分已归于限定行为': 'This component belongs to a restricted action.',
    '未采用联想': 'Excluded association',
    '从需要位于材料来源之前': 'From must precede the material source.',
    '从需要一个真实来源和一个喷射行为': 'From needs one real source and one spray action.',
    '材料来源与喷射行为不相容': 'The material source is incompatible with this spray.',
    '指定的材料来源已失效。': 'The bound material source is no longer available.',
    '本句只能从绑定的容器取材。': 'This clause can only draw from its bound container.',
    '—— 装备语句 ——': '--- Equipment clauses ---',
    '想象力 {cost} · 射程 {range} · 冷却 {cooldown}': 'Imagination {cost} · Range {range} · Cooldown {cooldown}',
    '目标：可见失控意识；刻痕保留 3 回合，下次合法命中兑现一次。': 'Target: visible hostile. A mark lasts 3 turns and redeems once on the next legal hit.',
    '本次瞄准点': 'This aimed cell',
    '已有征兆的失控意识': 'Hostile carrying a portent',
    '无意识体的留白': 'An unoccupied cell',
    '向需要唯一目标词和定向行为': 'Toward needs one target noun and one directed action.',
    '这个成分没有合法目标词义': 'This component has no target meaning.',
    '向的中心词没有合法定向行为': 'The head has no compatible directed action.',
    '向 {target} → 第 {n} 行': 'Toward {target} → Row {n}',
    '目标不符合定向语句。': 'The target does not match this directed clause.',
    '请选择定向语句的目标。': 'Choose a target for this directed clause.',
    '向所在行的功能词组合尚不成立': 'The function-word combination on this toward row is not supported.',
    '语句瞄准：方向键移动光标 · Enter 施放\n鼠标左键选目标 · O 辅助 · Esc / Q 取消': 'Sentence aim: arrows move cursor · Enter casts\nLeft click targets · O assists · Esc / Q cancels',
    '把需要位于处置对象之前': 'The direct-object marker must precede its patient.',
    '把需要后接一个处置对象和一个行为': 'The marker needs a patient followed by an action.',
    '缺少属性或方式来源': 'Missing a property or manner source.',
    '缺少中心词或行为': 'Missing a head or action.',
    '同一实体不能通过自身孔洞建立修饰关系': 'An item cannot modify itself through its own hole.',
    '功能词的关联成分存在歧义': 'The grammatical constituents are ambiguous.',
    '中心词没有合法行为': 'The head has no valid action.',
    '方式词义与这个行为不相容': 'This manner is incompatible with the action.',
    '缺少合法属性或处置对象': 'Missing a valid property or patient.',
    '属性与中心词的行为不相容': 'This property is incompatible with the head action.',
    '处置行为不能接受这个对象类型': 'This action cannot accept that patient type.',
    '前面的装备提供属性，后面的装备为中心词，不另领独立行为收益。': 'The left item provides a property to the right head, without claiming a separate action.',
    '把合法方式绑定行为，不把任意属性变成额外创伤。': 'Bind a valid manner to an action; arbitrary properties do not become extra damage.',
    '标记后接成分为处置对象，再与其后的合法行为绑定。': 'Mark the following item as a patient, then bind it to the subsequent valid action.',
    '改变施受关系；承受者、实际施事和作用类型必须明确。': 'Flip the passive relation; the sufferer, the actual agent and the effect type must all be explicit.',
    '被需要左侧承受者和右侧作用': 'Passive needs a sufferer on the left and an effect on the right.',
    '被的关联成分存在歧义': 'The passive relation has ambiguous constituents.',
    '同一实体不能既是承受者又是作用': 'One item cannot be both the sufferer and the effect.',
    '这个作用还没有可观察的外界入口': 'This effect type has no observable external entry yet.',
    '这个行为还没有对应的被动响应': 'This behavior has no matching passive response yet.',
    '承受者没有可被动触发的行为': 'The sufferer has no behavior that can trigger passively.',
    "条件": "Condition", "载体": "Carrier", "修饰": "Modifier",
    "行为": "Verb", "对象": "Object", "补语": "Complement",
    "斩击": "Slash", "刀痕": "Cutting mark", "锋利": "Sharp",
    "印下": "Imprint", "点燃": "Ignite", "余温": "Warmth",
    "静电": "Static charge", "护持": "Shelter", "回流": "Reflow",
    "照见": "Reveal", "节拍": "Tempo", "静谧": "Quiet", "霜意": "Frost",
    "喷射液体": "Spray liquid", "喷射气体": "Spray gas",
    "免费预览；确认后耗一次整理行动。": "Preview freely; confirming spends one arrangement action.",
    "逐行成句；位置与旋转改变含义，缺少行为则休眠。": "Each row forms a sentence. Position and rotation change meaning; without a verb it stays dormant.",
    "({x},{y}) {role}：{meaning}": "({x},{y}) {role}: {meaning}",
    "移动或旋转后，按占据的列自动解释。": "Position and rotation determine meanings automatically.",
    "同一实例多格发声，数值只计一次。": "One physical item may speak in several cells; its numeric value counts once.",
    "成功反馈：想象 1 · 家族冷却 6 回合": "Successful response: 1 imagination; shared family cooldown 6 turns",
    "近战：基础 1 + 装备 {bonus} · 耗时 {time}": "Melee: base 1 + equipment {bonus}; time {time}",
    "第 {n} 行：{text}": "Row {n}: {text}",
    "联想盘已迁移为位置语句；旧握持、词义与线路仅保存在迁移快照中，请检查当前句子。": "The board now uses position sentences. Old wielding, meanings and wiring remain in the migration snapshot; please review the current sentences.",
    "位置决定含义，不再切换握持或词义。": "Position determines meaning; wield and meaning switches have been removed.",
    "容器中没有可用的对应材料。": "The container has no usable material of the required medium.",
    "语句反馈·{effect}：在 {x},{y} 兑现一次联想。": "Sentence response · {effect}: one association at {x},{y}.",
    "没有合法的装备语句目标。": "No valid target for the equipment sentence.",
    "装备语句的目标、消耗或冷却条件不满足。": "The sentence's target, cost or cooldown requirements are not met.",
    "刀痕印在目标上：下一次合法命中兑现一次，保留 3 回合。": "A cutting mark awaits the next valid hit; expires in 3 turns.",
    "整理行动已经结束，但盘面条件改变，新布局未启用。": "The arrangement action finished, but conditions changed; the new layout was not activated.",
    "请选择本次动作的发射方式": "Choose the firing method for this action",
    "本次动作选项已经失效": "This action choice is no longer available",
    "没有成立的对应动作句": "No valid sentence provides this action",
    "使用": "Use",
    "披覆": "Cover",
    "维持": "Maintain",
    "放在行为列，与真实意象组成句子；没有载体或载荷不生效。": "Place in the verb column with a real image; without a carrier or payload it has no effect.",
    '存下这一刻不耗想象力；释放时采用后续标点的消耗与冷却。': 'Holding a moment costs no imagination; release uses the following marks\' costs and cooldowns.',
    '等待 {delay} 回合；释放时想象力 {cost} · 共享冷却 {turns} 回合': 'Wait {delay} turns; on release: imagination {cost} · shared cooldown {turns} turns',
    '再试着联想': 'try to respond again',
    "本义·握持": "True meaning · wield",
    "本义": "True meaning",
    "借意": "Borrowed meaning",
    "握住{item}后，用它攻击；收着备用时不会叠加攻击能力。": "Wield {item} to attack with it; reserve weapons add no extra attack.",
    "{item}暂时只是安静的念头，不带来原本的装备能力。": "{item} is a quiet thought for now, without its original abilities.",
    "借{item}来表达「{semantics}」，让同一分句的标点产生联想；暂时放下它原本的能力。": "Use {item} to express {semantics} and give meaning to punctuation in the same clause; set its original ability aside.",
    "带着{item}，便能获得它本来的能力：{effect}": "Carry {item} for its original ability: {effect}",
    "冒号·湿润": "Colon · wet condition",
    "问号·留白": "Question mark · blank condition",
    "括号·护持": "Parentheses · shelter",
    "破折号·移涌": "Dash · flow",
    "感叹号·放电": "Exclamation · discharge",
    "着重号·余温": "Emphasis · warmth",
    "引号·轻声": "Quotes · whisper",
    "省略号·回响": "Ellipsis · echo",
    "顿号·并列": "Enumeration comma · parallel responses",
    "句号·断句": "Period · new clause",
    "冒号·命中": "Colon · on hit",
    "冒号·受击": "Colon · on hurt",
    "冒号·接触": "Colon · on contact",
    "冒号·构想": "Colon · on conception",
    "逗号·连词": "Comma · join words",
    "分号·断句": "Semicolon · new clause",
    "只有触发位置能够导电，这一分句的联想才会发生。": "This clause responds only when the triggering place conducts electricity.",
    "想象力不高于留白意象的阈值时才联想；没有阈值意象时取 10。": "Respond only at or below the blank image's imagination threshold; use 10 if no threshold image is present.",
    "借助护的意象，护住下一次创伤：少受 1 点，保留 3 回合。": "With a shelter image, reduce the next trauma by 1; it lasts 3 turns.",
    "借助湿的意象，把触发格最多 5 单位导电液体移向液体较少的合法邻格。": "With a wet image, move up to 5 units of conductive liquid to a legal neighbour with less liquid.",
    "借助电的意象，向触发位置附近的湿润敌人放出 1 点微弱电击。": "With an electric image, give a wet foe near the triggering place a faint 1-point shock.",
    "借助热的意象，点燃一个可燃位置；初始火焰强度为 1。": "With a heat image, ignite a flammable place with flame strength 1.",
    "借助声的意象，在落点响起半径 2 的轻声，吸引附近意识。": "With a sound image, make a quiet sound within radius 2, drawing nearby minds.",
    "借助拍的意象，让这一分句的联想延后 2 回合；最多留一件事，4 回合后失效。": "With a rhythm image, delay this clause by 2 turns; only one event can be held, and it expires after 4 turns.",
    "让同一事件并列多个联想，按阅读顺序尝试；没有顿号时只采用第一个。共用消耗与冷却。": "Try several responses to the same event in reading order; without this comma, use only the first. Costs and cooldowns are shared.",
    "结束这一分句。后面的词与条件从头读，不借用前面的意象。": "End this clause. The following words and conditions begin anew, without borrowing earlier images.",
    "后面的联想在你命中目标时尝试。": "Try the following responses when you hit a target.",
    "后面的联想在你受到实际创伤时尝试。": "Try the following responses when you suffer actual trauma.",
    "后面的联想在你进入液体或气体时尝试。": "Try the following responses when you enter liquid or gas.",
    "后面的联想在你成功施放构想时尝试。": "Try the following responses when you successfully unfold a conception.",
    "从左到右、从上到下读词；每个意象只读一次。": "Read left to right, top to bottom; each image counts once.",
    "逗号连词，分号或句号断句；旋转只改变占地形状。": "Commas join words; semicolons and periods start new clauses. Rotation only changes the shape.",
    "这场梦写成：": "The dream reads:",
    "想让梦回应行动，可以在词旁放入标点；无需接线。": "Place punctuation beside your words to let the dream respond to actions. No wiring is needed.",
    "旋转只改变形状；液体自动流向较空的合法邻格。": "Rotation changes only shape. Liquid flows to an emptier legal neighbour.",
    "水源是触发位置，流向较空的合法邻格": "Liquid comes from the triggering place and flows to an emptier neighbour",
    "已读入句子": "Read into the sentence",
    "分句标点": "Clause punctuation",
    "还需 {n} 回合": "Ready in {n} turns",
    "读句 v": "Read v",
    "摆放 v": "Place v",
    "启用 c": "Use c",
    "写定": "Write",
    "联想 {paths} 句 · 未写下 {broken} 词 · [ 整理": "{paths} responses · {broken} unwritten words · [ Arrange",
    "m 切换本义与借意 · c 写下或收起这个词\n本义使用装备本来的能力；借意把它的含义交给标点。": "m true / borrowed meaning · c write or withdraw this word\nTrue meaning gives the original ability; borrowed meaning gives punctuation its imagery.",
}

# ---- 联想盘功能词与句子来源行（2026-10-24 玩家可见英文补漏）----
EN_EQUIPMENT.update({
    # 功能词标签（盘面工具/手里/检视）
    '被': 'by',
    '向': 'to',
    '从': 'from',
    '只': 'only',
    # 功能词说明（检视面板逐词解释）
    '让左右两侧共同构成一次行动；同一次行动不会重复计算消耗。':
        'Both sides form one action; that action does not pay twice.',
    '每次只能选择一侧的行为；两侧不会同时生效。':
        'Choose one side each time; both sides never take effect together.',
    '满足关联装备提供的条件时，才执行后面的行为；“如果”本身不提供条件。':
        "Run the action only when the linked equipment's condition holds; IF itself supplies no condition.",
    '对应的“如果”条件不满足时才执行这里的行为；行动资源不足不会转入“否则”分支。':
        'Run this branch only when the matching IF condition is false; insufficient resources do not fall through.',
    '把后面的内容交给行为作用，例如把刀痕印在目标上，或把瓶中材料喷向目标。':
        'Hand the payload to the action, such as imprinting a mark or spraying material from a bottle.',
    '左侧装备改为受击响应，右侧装备决定响应哪类创伤；相应创伤实际结算后才会触发。':
        'Turn the left equipment into a hit response; the right side selects the damage kind that triggers it.',
    '指定行动瞄准的目标；原有射程和视线限制仍然有效。':
        "Set the action's target; existing range and line-of-sight limits still apply.",
    '从后面的容器取用已有液体或气体，再交给对应装备喷射；容器为空时不会凭空产生材料。':
        'Draw existing liquid or gas from the container for the linked action; empty containers create nothing.',
    '把前面装备切换为属性来源，修饰后面的行为：刀锋增加锋利，余温或静电附加命中反馈，节拍让本次行为更快；属性来源不会额外执行自身行为。':
        'Treat the left equipment as a property source for the action; it does not perform a second action.',
    '把前面装备切换为行为方式，例如用饰品的轻快节拍缩短后续攻击耗时；方式只修饰关联行为，不支持的组合无法成句。':
        'Turn the left equipment into a manner for the action; unsupported combinations cannot form a sentence.',
    '只让选定的那件事发生；同句里用于修饰或附加效果的其他词义这一回都不参与。':
        'Only the selected action happens; other modifiers or feedback in the row do not participate this time.',
    '前一次确实造成创伤后，才会追加一次；追加前会重新检查资源，两次共用本次行动的消耗和创伤额度。':
        'Append one more attempt only after the first actually dealt damage; resources are rechecked and both share the budget.',
    # 行为词/标点/线材说明
    '放在“行为”列，并搭配能执行这项动作的意象；单独放置不会生效。':
        'Place it in the Action column together with an image that can perform the action; alone it does nothing.',
    '借助湿的意象，把触发格中最多 5 单位导电液体移向有容量的相邻位置。':
        'With damp imagery, move up to 5 units of conductive liquid from the triggered cell to a neighbour with capacity.',
    # 说明区「来源行」与效果详情前缀
    '{source}来自盘面第 {rows} 行': '{source} comes from board rows {rows}',
    '这项持续效果': 'This ongoing effect',
    '这条反应': 'This response',
    '这条语句': 'This sentence',
    '效果详情：': 'Effect: ',
    # 医院装备词义（检视/成句共用）
    '相接': 'adjacent',
    '病原体': 'pathogen',
})

# ---- 联想盘句子明细、可读原因与持续效果短语（2026-10-24 英文补漏）----
EN_EQUIPMENT.update({
    # 句子明细模板
    '这行还没有组成完整意思。': 'This row does not form a complete meaning yet.',
    '这组意象暂时无法组合，请调整相关装备或功能词的位置。':
        'These images cannot be combined yet; adjust the equipment or grammar words.',
    '补语只随持续契约生效；这一句是即时行为，补语暂不参与。':
        'A complement only applies to a sustained contract; this clause is an instant action, so the complement sits out.',
    '留白带来的额外回流合计最多 3 点；多件装备按各自的想象力门槛生效，并沿用递减。':
        'Blank-space inflow totals at most 3 points; multiple items apply at their own Imagination thresholds with diminishing returns.',
    '两次出手共用一次行动的创伤上限，总创伤不会增加。':
        "Both strikes share one action's trauma cap, so total trauma does not increase.",
    '随句补足：{item}——{ending}': 'Supplied with the clause: {item} — {ending}',
    '词义切换：{item}的节拍只缩短关联攻击的耗时；同一装备已提供持续攻速时，不重复叠加。':
        "Meaning switch: {item}'s beat only shortens the linked attack; an ongoing attack-speed effect from the same item does not stack.",
    '未采用：{item}提供的“{modifier}”{label}不生效。':
        'Not used: the “{modifier}” {label} from {item} has no effect.',
    '{item}让本句喷射多带出材料；仅从容器取材时生效，不超过容器余量。同一件装备的持续效果不重复计算。':
        "{item} makes this spray carry more material; it works only when drawing from a container and never beyond its contents. The same item's ongoing effect is not counted twice.",
    '{item}让本句修缮补得更多；仍消耗原有工具，完整度不超过墙体上限。同一件装备的持续效果不重复计算。':
        "{item} makes this repair restore more; it still consumes the usual tool and never exceeds the wall's integrity cap. The same item's ongoing effect is not counted twice.",
    '{item}让本句弹体多一分穿透；遇墙仍会耗去穿透额度，免疫弹体的墙体不受影响。同一件装备的持续效果不重复计算。':
        "{item} gives this shot one more point of penetration; walls still spend that allowance, and walls immune to projectiles are unaffected. The same item's ongoing effect is not counted twice.",
    '{item}让本句攻击认出残留的附着；目标仍有附着时，创伤至多多 1 点。同一件装备的持续效果不重复计算。':
        "{item} lets this attack recognise lingering attachment; if the target is still attached, trauma is at most 1 higher. The same item's ongoing effect is not counted twice.",
    '{item}让本句命中或喷射落点借液体传导；落点和附近目标都须有导电液体，只多传 1 点创伤。成功消耗 1 点想象力，并受反馈冷却限制。':
        '{item} lets this hit or spray conduct through liquid; the landing cell and nearby targets need conductive liquid, for at most 1 extra trauma. A success costs 1 Imagination and respects feedback cooldown.',
    '{item}让本句命中带出余温；只在有可燃材料的位置点火。成功消耗 1 点想象力，并受反馈冷却限制；不凭空生成燃料。':
        '{item} leaves an ember on this hit; it ignites only where there is flammable material. A success costs 1 Imagination and respects feedback cooldown; no fuel is created.',
    '{item}让本句命中带出余爆，最多波及附近一个可见目标 1 点创伤；不穿墙。成功消耗 1 点想象力，并受反馈冷却限制。':
        '{item} adds a small blast to this hit, dealing at most 1 trauma to one nearby visible target; it does not pass through walls. A success costs 1 Imagination and respects feedback cooldown.',
    '{item}借甩手的力道强化本句攻击，与武器创伤按原有规则共同计算；只修饰本句，不额外投出或消耗一件物品。':
        '{item} strengthens this attack through a throwing motion and combines with weapon trauma under the usual rules; it modifies this clause only and throws or consumes nothing extra.',
    # 可读原因（内部原因键；readable_reason 在英文模式优先取这些）
    '缺少行为': 'The sentence has no executable action yet.',
    '盘面物理无效': 'The layout conflicts; adjust the positions of the images or grammar words.',
    '缺少真实载体或效果载荷': 'There is no item here that can perform this action.',
    '这个载体不能形成持续契约': 'This item cannot serve as an ongoing effect source.',
    '这个行为不能改成持续契约': 'This action cannot be sustained with “maintain”.',
    '披覆需要护持载荷': '“Cover” needs a protective effect to pair with.',
    '载体没有可用行为': 'The current item position has no executable action.',
    '点燃不接受这种载荷': '“Ignite” only accepts heat-type payloads.',
    '持续行为与对象类型不相容': 'This ongoing effect cannot apply to that object type.',
    # 持续效果短语（随句补足 / 省示）
    '涉水时侵扰减轻': 'Less harassment while wading',
    '出手更轻快': 'Strike more swiftly',
    '心智的伤口浅一些': 'Mind wounds are shallower',
    '清醒的伤口浅一些': 'Lucidity wounds are shallower',
    '心智与清醒的伤口都浅一些': 'Mind and Lucidity wounds are both shallower',
    '它替你留意着心智': 'It watches over your Mind',
    '火燎上来时轻一些': 'Less burning when fire catches',
    '静电不再跳到你身上': 'Static no longer jumps to you',
    '脚步声轻了': 'Lighter footsteps',
    '太吵的地方它替你挡一半': 'It halves the noise in loud places',
    '靠近它的东西慢半拍': 'Things near it slow by half a beat',
    '照亮更远处': 'Lights farther away',
    '隔着墙也听得出虚实': 'Sense through walls',
    '修补得更彻底': 'Repairs more thoroughly',
    '看得更远': 'See farther',
    '靠近你的静电会跳': 'Static near you arcs',
    '爆裂波及更宽': 'Blasts spread wider',
    '点火时火势更旺': 'Fires burn hotter when lit',
    '针脚扎得更深': 'Stitches bite deeper',
    '捡拾更快': 'Pick up faster',
    '喷得更足': 'Spray more',
    '沾过气味的逃不远': 'Scented prey cannot flee far',
    '湿处也照常导电': 'Conducts even when wet',
    '散场时的收获多一分': 'A little more loot when the show ends',
    '下一次创伤轻一点': 'The next wound is lighter',
    '身上的附着它一直滤着': 'It keeps filtering what clings to you',
    '构想展开后，想象力回得快': 'Imagination returns faster after a conception',
    '挨了打，它帮你洗短征兆': 'When hit, it shortens an omen for you',
    '有光时它替你挡一下': 'In the light it shields you once',
    '挨打时它响一声': 'It sounds when you are struck',
    '吃下的东西它补一点': 'It restores a little of what you ingest',
    '有光时它照出伪装': 'In the light it reveals disguises',
    '爆炸撞上来时，清醒的伤口浅一些': 'Lucidity wounds are shallower against explosions',
    '跨过门后，下一次出手多一分力': 'After crossing a doorway, your next strike has extra force',
    '再次命中认得的异象时，记起它的完整度': 'Hitting a known anomaly again recalls its integrity',
    '迈出一步，就标出相邻能走的连接': 'Each step maps the neighbouring connections',
    '独处时，自然恢复多回来一点': 'A little more natural recovery when alone',
    '命中后，照出目标周围一格的动静': 'After a hit, reveal movement within one cell of the target',
    '替你拒绝一次弱控制': 'Refuses one weak control for you',
    '触到与上次不同的状态时，视野暂时开阔一格': 'Touching a different state briefly widens sight by one',
    '命中后，指出一个相邻空位': 'After a hit, point out an adjacent empty cell',
    '悬停时能读出到目标的最短步数': 'Hovering reads the shortest path to a target',
    '把一件易逝物挂上梦的墙，替你承受一次打击': 'Hang a perishable on the dream wall to take one blow for you',
    '跳弹命中后留下折射印记，换个方向命中便能伤得更深': 'Ricochets leave a refraction mark; striking from another direction hurts deeper',
    '每层首次亲手点火后，下一步可以免费走，近处追兵暂时跟丢': 'After your first ignition on a layer, the next step is free and nearby pursuers lose you',
    '一次声响引来目标后，下次声波会让声源附近的意识震停一拍': 'After a sound draws a target, your next wave stuns nearby minds for a beat',
    '每层一次，想象力耗尽后可以免去一次构想的想象力消耗': 'Once per layer, a conception costs no Imagination after yours runs out',
    '想象力低落时，回流会多回来一点': 'When Imagination is low, a little more flows back',
    '投得更远，落点的冲击也更重': 'Thrown farther, with a heavier impact',
    '护持一直都在': 'The protection is always there',
    '那份效果一直都在': 'That effect is always there',
    '想象力不超过 {threshold} 时，每回合多回流 {power} 点想象力':
        'While Imagination is at most {threshold}, {power} more Imagination flows back each round',
    # 修饰/方式/裸修饰词与排除标签
    '喷射强化': 'spray boost',
    '追迹': 'tracking',
    '爆裂': 'blast',
    '锋利地': 'sharply',
    '轻快地': 'swiftly',
    '以更强的穿透力': 'with greater penetration',
    '带着余温': 'with an ember',
    '增加喷射量': 'with more spray',
    '追踪已有征兆的目标': 'tracking targets that carry a portent',
    '带着余爆': 'with a small blast',
    '更充分地': 'more fully',
    '借投掷的手法，': 'using a throwing motion, ',
    '借液体导电': 'conducting through liquid',
    '轻快节拍': 'swift beat',
    '穿透力': 'penetration',
    '追迹气味': 'tracking scent',
    '余爆': 'small blast',
    '修缮手艺': 'repair craft',
    '投掷手法': 'throwing technique',
    '导电力': 'conductivity',
    '命中后点燃': 'ignites on hit',
})

# ---- 藏书宫/疗所装备的功能词义（2026-10-24：检视与成句回退路径漏翻）----
EN_EQUIPMENT.update({
    '跨门后': 'after crossing a doorway',
    '记起': 'recall',
    '折返': 'fold back',
    '独处': 'when alone',
    '汇聚': 'combine',
    '拒绝': 'refuse',
    '变化后': 'after a change',
    '存疑': 'doubt',
})

# ---- 扩展装备运行期文案（2026-10-25：terrain / projectile / circuit 三族主动路径）----
EN_EQUIPMENT.update({
    '这里没有符合条件的真实对象；没有消耗。':
        'There is no real target here that fits; nothing was spent.',
    '{item}完成了操作。': '{item} carried out the action.',
    '{item}是被动的：脚更沉（每次移动多付时间），没有可以直接做的动作。':
        '{item} is passive: heavier footing (every move costs extra time); there is no direct action.',
    '{item}是被动的：只在你操作电路那一次少沾一份液面。':
        '{item} is passive: it spares one liquid attachment the time you work a circuit.',
    '{item}是被动的：换弹时掉出的实弹落在脚下，可以再捡回来。':
        '{item} is passive: live rounds dropped while reloading land at your feet and can be picked up again.',
    '{item}是被动的：换弹中允许走一小步，一次换弹只给一步。':
        '{item} is passive: one short step during a reload, one step per reload.',
    '{item}只吸得到最上面那一种——瓶里混着好几种，它分不开。':
        '{item} can only draw the topmost kind; the bottle holds several and it cannot separate them.',
    '{item}还没定下要滤哪一种杂质——容器里至少要有两种液体。':
        '{item} has not fixed on an impurity yet; the container needs at least two liquids.',
    '{item}接不住{material}——它凝不成障碍，所以没有接住。':
        '{item} cannot catch {material} — it will not set into a barrier, so nothing was caught.',
})

# ---- 扩展装备运行期文案（2026-10-25：realm 批 · 病区／书库交界）----
EN_EQUIPMENT.update({
    '{item}的废料格满了——这一趟夹不了新的了。':
        '{item}\'s scrap tray is full — nothing new can be scraped on this run.',
    '{item}没有可剥离的负面附着——只有带真实材料的那种刮得下来。':
        '{item} finds no strippable negative attachment — only ones carrying real material can be scraped off.',
    '{item}只托得住 {n} 件——先取走一件。':
        '{item} holds only {n} pieces — take one out first.',
    '{item}包不住——行囊里没有可包的学习物。':
        '{item} has nothing to wrap — no learnable tome in the pack.',
    '{item}里没有可拆的恢复品——得先有一份真实的。':
        '{item} has no restorative to split — one real dose is needed first.',
    '{item}只抄得下真实的交互条件——这一格既不是设施，也没有节点读数。':
        '{item} only copies real interaction conditions — this cell is neither a facility nor a node reading.',
    '{item}收住了——这一下会牵动一单还没走完的梦。':
        '{item} holds back — that blow would disturb a dream still in progress.',
    '{item}探到一跳——电场顺着针柄过了一遍手。':
        '{item} finds one hop — the field runs back down the handle into your hand.',
    # ---- realm 信息类件的反馈（作用就是「给出信息」，不能只说「完成了」）----
    '{item}抄下了一处交互条件：{n} 条读数。':
        '{item} copies down one set of interaction conditions: {n} readings.',
    '{item}抄下了一处设施的交互条件。':
        '{item} copies down the interaction conditions of one facility.',
    '{item}沿直线标出了 {n} 格已见地形。':
        '{item} marks {n} seen cells in a straight line.',
    '{item}翻到背面：{a}（费 {ca}／冷 {cda}）对 {b}（费 {cb}／冷 {cdb}）。':
        '{item} turns the card over: {a} (cost {ca} / cooldown {cda}) against {b} (cost {cb} / cooldown {cdb}).',
})
