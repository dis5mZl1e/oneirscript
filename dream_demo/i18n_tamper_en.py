"""English text for the tampering system (chaos tiers, risk events, the Omitted)."""

EN_TAMPER = {
    '篡改 · 地图观察': 'Tamper · Map observation',
    '[返回编辑 V]': '[Return to editing V]',
    '[查看地图 V]': '[View map V]',
    '[取消篡改]': '[Cancel tampering]',
    '[确认]': '[Confirm]',
    '[取消]': '[Cancel]',
    '目标：{name}': 'Target: {name}',
    '完整度 {n} · {alert}': 'Integrity {n} · {alert}',
    '选词：{word}': 'Word: {word}',
    '观察格：({x},{y})': 'Observed tile: ({x},{y})',
    '编辑不推进回合；V 查看地图。': 'Editing takes no turns; V views the map.',
    '已选 {n}/3': 'Selected {n}/3',
    'Tab 切条件 · Space 勾选 · [ ] 换组合 · Enter 执行 · Esc 返回': 'Tab conditions · Space toggle · [ ] combinations · Enter commit · Esc back',
    '↑↓ 选词 · Tab 切条件 · Space 勾选 · Enter 进确认 · Esc 退出': '↑↓ words · Tab conditions · Space toggle · Enter preview · Esc close',
    '▾ 详情（\\ 收起）': '▾ Details (\\ fold)',
    '▸ 详情（\\ 展开）': '▸ Details (\\ expand)',
    '原句：{sentence}': 'Original: {sentence}',
    '条件互斥或已选满三个，请先取消一项。': 'These conditions conflict or three are already selected. Uncheck one first.',
    '脚步准备 −{n}': 'Prepared step −{n}',
    '移动声影（下一拍）声响半径：{n}': 'Echo in motion (next beat), sound radius: {n}',
    '连续压力 {pressure}/3 · 风险 {tier}；可能产生声响、余火或异象警戒变化。': 'Pressure {pressure}/3 · Risk {tier}; noise, embers or changes in enemy alertness may follow.',
    '你利用「{name}」调整自己，解除了「{portent}」。': 'You use {name} to recover, clearing {portent}.',
    '这里没有可以展开构想的位置。': 'There is no valid place to unfold this conception.',
    '镜面需要相邻的空地。': 'A mirror needs an adjacent empty tile.',
    '这里已经有一面构想的镜面。': 'A conceived mirror already stands here.',
    '构想「{name}」留在了梦境中（{turns} 回合）。': '{name} remains in the dream for {turns} turns.',
    '延迟的火花落下，开始点燃真实材料。': 'The delayed spark falls and ignites the material beneath it.',
    '构想残留：{name} · 剩余 {turns} 回合 · 朝向 {direction}': 'Conception: {name} · {turns} turns left · Direction {direction}',
    '对应征兆的负面积累降低 60%，新沾染时长缩短 50%（最低 1 回合）；仍会受到影响，同类耐受不叠加。': 'Matching harmful accumulation is reduced by 60%, and newly applied durations by 50% (minimum 1 turn). Exposure still affects you; matching resistances do not stack.',
    '耐受遮蔽': 'Resist Obscuration',
    '耐受冻僵': 'Resist Freezing',
    '耐受灼伤': 'Resist Scalding',
    '耐受辐射病': 'Resist Radiation Sickness',
    '耐受麻痹': 'Resist Numbness',
    '耐受迟钝': 'Resist Sedation',
    '耐受遮蔽与冻结': 'Resist Obscuration and Freezing',
    '耐受强遗忘': 'Resist Strong Oblivion',
    '耐受中毒': 'Resist Poison',
    '耐受倒带迟滞': 'Resist Rewind Lag',
    '耐受绊缚': 'Resist Snaring',
    '耐受失忆': 'Resist Amnesia',
    '耐受毒气': 'Resist Poison Gas',
    '耐受门扉眩晕': 'Resist Door Vertigo',
    '耐受缠住': 'Resist Snare',
    '这种液体没有可以蒸腾的产物。': 'This liquid has no evaporation product.',
    '环境适配规则已更新：已有构想、洞察与记忆碎片采用新版范围、声音和条件效果；持有内容与槽位保留，旧构想残留按原剩余期限结束，载入前梦痕已备份。': 'Environment rules updated: known conceptions, insights and memory fragments now use revised ranges, sound and conditional effects. Your possessions and slots remain. Existing conception traces retain their remaining lifetimes. Your save was backed up before loading.',
    '四系统规则已更新：记忆碎片改为耐受，洞察提供条件行动，构想与篡改采用新规则；原持有内容保留，迁移前梦痕已备份。': 'System rules updated: fragments grant resistance, insights grant situational actions, and conceptions and tampering use the new rules. Your possessions remain; a pre-migration save was backed up.',
    '旧梦痕里有 {n} 格地势绝对值达到 {step} 档以上（其中 {exact} 格正好是 {step} 的整数倍）。这既可能来自多次合法改造，也可能来自旧版把 {step} 当一档加减的错值；无法可靠区分，因此全部原样保留，不按数值猜测改写，迁移前梦痕已备份。可在地势视图核对。': 'This old dream contains {n} cells whose elevation magnitude reaches {step} tiers or more ({exact} of them are exact multiples of {step}). These may come from repeated legitimate reshaping or from an old build that added/subtracted {step} per tier; the two cannot be reliably told apart, so every value is preserved as-is rather than guessed at, and a pre-migration save was backed up. Check them in the elevation view.',
    '轻轻': 'Gently',
    '用力': 'Forcefully',
    '通常': 'Normal',
    '程度': 'Degree',
    '消散': 'Disperse',
    '使用原弱档效果与代价。': 'Use the weaker effect and its original cost.',
    '使用原强档效果与代价。': 'Use the stronger effect and its original cost.',
    '{name}：{sentence}': '{name}: {sentence}',
    '程度：{value}（点击或 - = 切换）': 'Degree: {value} (click or - = to change)',
    # 混乱度风险档位（规格 §7.1）：玩家可见的是档位名，不是概率。
    "微弱": "Faint",
    "不稳": "Unstable",
    "扭曲": "Distorted",
    "错乱": "Disordered",
    "失序": "Unraveling",
    # 风险事件名（规格 §7.2）：只在反馈里出现，事件池本身不揭示。
    "墨晕": "Ink Blur",
    "字痕": "Glyph Scar",
    "句尾回响": "Sentence Echo",
    "页边余火": "Margin Ember",
    "漏字来客": "Omitted Guest",
    "篡改风险": "Tamper Risk",
    "篡改风险专属": "Tamper risk exclusive",
    "不进投放池": "Not in spawn pools",
    # 风险结算反馈。
    "页边余火：纸边泛起焦痕，{n} 处地面开始发烫。":
        "Margin Ember: the paper edges scorch and {n} patches of floor grow hot.",
    "页边的焦痕烧起来了——{n} 处火场。":
        "The scorched margins catch fire — {n} fire patches.",
    "页边的焦痕冷了下去，没有烧起来。":
        "The scorched margins cool down without catching fire.",
    "页边余火烧完了。": "The margin embers burn out.",
    "句尾回响在你耳边重复了一遍。": "The sentence echo repeats itself at your ear.",
    "{label}：改过的句子在你脑后回响。": "{label}: the altered sentence echoes behind your head.",
    "漏字来客：句子的空缺里站出一个人形——脚步声总少一拍。":
        "Omitted Guest: a figure steps out of the gap in the sentence — its footsteps always miss a beat.",
    "清醒创伤 {n}": "lucidity trauma {n}",
    "心智创伤 {n}": "mind trauma {n}",
    "想象创伤 {n}": "imagination trauma {n}",
    # 漏字者与「吞音」（规格 §7.3）。
    "漏字者": "The Omitted",
    "一个人形站在句子的空缺里。它走近时，脚步声总少一拍。":
        "A figure stands in the gap of a sentence. As it draws near, its footsteps are always one beat short.",
    "吞音": "Swallowed Sound",
    "它停住脚步，张开没有声音的口。你刚想起的词开始变淡。":
        "It stops and opens a soundless mouth. The word you just recalled begins to fade.",
    "目标在视线内且距离不超过 4 格；你又完成一次耗时行动后结算。":
        "Target in line of sight and within 4 tiles; resolves after your next time-consuming action.",
    "拉开距离、走出视线，或让那句话先落地。":
        "Gain distance, break line of sight, or let that sentence land first.",
    "{enemy}张了张口，声音没有找到你。": "{enemy} opens its mouth; the sound does not find you.",
    "{enemy}吞掉了你刚想起的词（想象创伤 {n}）。":
        "{enemy} swallows the word you just recalled (imagination trauma {n}).",
    # 提交与验证反馈（规格 §5）。
    "你把「{before}」改成了「{after}」。": "You changed “{before}” into “{after}”.",
    "混乱度 {chaos}（{tier}）": "Chaos {chaos} ({tier})",
    "想象力不够（需要 {n}）。": "Not enough imagination (needs {n}).",
    "这个地点已经没有可改的句子了。": "This place has no editable sentences left.",
    "这笔交易已经完成，改不动了。": "That trade is already done; it cannot be altered.",
    "这句话已经不在货架上了。": "That line is no longer on the shelf.",
    "没有这段文字。": "There is no such text.",
    "这个改动不合法。": "That edit is not allowed.",
    "这段文字不在眼前。": "That text is not in front of you.",
    "这处修改已经落地了。": "That edit has already been applied.",
    "这句话已经变了——重新看一下再改。": "That sentence has changed — look again before editing.",
    "从当前这句改不出那一笔。": "That edit cannot be made from the current sentence.",
    # 设置页（规格 §4.1：改键项）。
    "篡改键": "Tamper Key",
    "对话中打开篡改面板的按键；只在该上下文生效。":
        "Key that opens the tampering panel in dialogue; it only works in that context.",
    # 旁侧面板与键鼠提示（规格 §4.2、§4.4）。
    "篡改": "Tamper",
    "[{key}] 篡改": "[{key}] Tamper",
    "想象力 {imagination} · 混乱度 {chaos}（{tier}）": "Imagination {imagination} · Chaos {chaos} ({tier})",
    "这里已经没有可改的位置了。": "No editable positions are left here.",
    "选词": "Pick a word",
    "位置": "Position",
    "预览": "Preview",
    "{heading}：{word}": "{heading}: {word}",
    "位置 {index}/{total}": "Position {index}/{total}",
    "想象 {cost} · 混乱 +{chaos}": "Imagination {cost} · Chaos +{chaos}",
    "想象力 −{cost} · 混乱度 +{delta} → {chaos}（{tier}）":
        "Imagination −{cost} · Chaos +{delta} → {chaos} ({tier})",
    "确认": "Confirm",
    "↑↓ 选词 · Enter 看位置 · Esc 收起": "↑↓ pick a word · Enter show positions · Esc close",
    "←→ 换位置 · ↑↓ 换句子 · Enter 预览 · Esc 回词表":
        "←→ move position · ↑↓ move sentence · Enter preview · Esc back to words",
    "Enter 确认 · Backspace 回词表 · Esc 退回": "Enter confirm · Backspace back to words · Esc back",
    # 旧档兼容（规格 §9.3）。
    "有一处改动引用的写法已不在这一版梦里，那句话恢复了原样。":
        "One edit referred to a wording that is gone from this version of the dream; that sentence is back to its original form.",
    "有一处改动引用的句子已不在这一版梦里，它恢复了原样。":
        "One edit referred to a sentence that is gone from this version of the dream; it is back to its original form.",
    # ---- 地图篡改：条件词（docs §四/五/六）----
    "趁虚": "Exploit the Crack",
    "趁它未察觉": "Catch It Unaware",
    "以声代想": "Pay with Noise",
    "以想代声": "Pay with Thought",
    "这面墙已有裂痕：这一笔的完整度伤害提高到 1.5 倍。":
        "The wall is already cracked: this blow deals 1.5× integrity damage.",
    "它还没察觉：这次惊散的时长翻倍。":
        "It has not noticed you yet: the spooking duration doubles.",
    "效果结算后，你所在的位置发出基础半径 8 的声音；想象力少付 1 点。":
        "After the effect resolves, your position emits sound with base radius 8; the edit costs 1 less imagination.",
    "这次尖声呼唤不再发出声音；想象力多付 2 点。":
        "This clamor makes no sound at all; it costs 2 extra imagination.",
    "完整度": "Integrity",
    "意志": "Will",
    "行动": "Action",
    "声响": "Sound",
    "燃点": "Ignition point",
    "湿度": "Moisture",
    "没有这个条件。": "There is no such condition.",
    "这个条件用不到这个字词上。": "That condition does not apply to this word.",
    "这个条件组合用不到这个字词上。": "That condition combination does not apply to this word.",
    "这里没有可以趁虚的墙。": "There is no wall here to exploit.",
    "这面墙还完好，趁不了虚。":
        "This wall is still intact — there is no crack to exploit.",
    "它已经察觉了，趁不上这一手。":
        "It is already alert; you cannot catch it unaware.",
    "，你所在的位置也会发出声音": ", and your position will also emit sound",
    "，可这一声没能传出去": ", but this sound will not carry",
    "{base}{extra}": "{base}{extra}",
    "{base} {extra}": "{base} {extra}",
    "（条件：{name}）": " (Condition: {name})",
    # 方位与多对象指代（2026-10-18 docs 第 8 节第二批）
    "北": "north", "东北": "northeast", "东": "east", "东南": "southeast",
    "南": "south", "西南": "southwest", "西": "west", "西北": "northwest",
    "脚下": "underfoot",
    "{direction}侧": "to the {direction}",
    "{direction}的{name}": "{name} {direction}",
    "{direction}近处的{name}": "the nearer {name} {direction}",
    "{direction}远处的{name}": "the farther {name} {direction}",
    "{direction}{number}号{name}": "{name} #{number} {direction}",
    "{direction}第{number}处{name}": "{name} (spot {number}) {direction}",
    # 全视野范围与批量报价（2026-10-18 docs 第 8 节第四批）
    "这个范围还没有开放。": "That range is not available yet.",
    "这个字词不支持全视野范围。": "This word does not support the full-view range.",
    "这一局已经结束。": "This run is over.",
    "视野内没有可以{action}的对象。": "Nothing in view can be {action}.",
    "视野内的目标都不满足这个条件（{n} 处被排除：{reason}）。":
        "No target in view meets this condition ({n} excluded: {reason}).",
    "视野内可破坏的墙体": "destructible walls in view",
    "视野内可点燃的东西": "flammable things in view",
    "视野内可催生的植物": "plants that can be grown in view",
    "视野内可枯萎的植物": "plants that can be withered in view",
    "视野内的目标": "targets in view",
    "{shown}等 {n} 处。": "{shown} and {n} more.",
    "（全视野 {n} 处；想象力 −{cost}，混乱度 {chaos}／{tier}）":
        " (full view: {n} targets; imagination −{cost}, chaos {chaos}/{tier})",
    # 全视野/原句布局（2026-10-18 docs 第 8 节第六批）
    "范围：{mode}（R 或点击切换）": "Range: {mode} (R or click to switch)",
    "全视野": "full view", "这一处": "this spot", "原句：": "Original: ",
    "落点：未选（V 查看地图后移动光标选择）":
        "Destination: not selected (press V and move the cursor on the map)",
    "落点：观察格 ({x},{y})（V 查看地图可改）":
        "Destination: cursor cell ({x},{y}) (V to change)",
    "范围提示：{label} · {n} 处 · 排除 {excluded} 处":
        "Range: {label} · {n} targets · {excluded} excluded",
    "{label}（{n} 处）将按当前字词统一生效。":
        "{label} ({n} targets) will be affected by the current word together.",
    "代价（全视野 {n} 处）：想象力 {a} · 混乱 +{b}":
        "Cost (full view, {n} targets): imagination {a} · chaos +{b}",
    # 视野溢出说明（2026-10-20 docs 第 15 节第三批）
    "另有 {n} 处同类在视野里没被点名（走近或悬停可换目标）":
        "{n} more of the same kind are in view but unnamed (step closer or hover to switch)",
    # 流体守恒计划（2026-10-18 docs 第 8 节第五批）
    "这个字词不支持流体搬运。": "This word does not support fluid transfer.",
    "这里没有可以搬运的流体。": "There is no fluid here to move.",
    "聚流需要先选定一个明确落点。": "Gathering needs an explicit destination first.",
    "落点不能就在来源里。": "The destination cannot be inside the source.",
    "落点不在地图内。": "That destination is outside the map.",
    "落点不在视野内。": "That destination is out of view.",
    "来源里有不同材料，不能一次搬运。":
        "The source contains different materials and cannot be moved at once.",
    "落点没有与来源相邻。": "The destination is not adjacent to the source.",
    "落点放不下这种材料。": "That destination cannot hold this material.",
    "这个区域里有不同材料，不能一次搬运。":
        "This region contains different materials and cannot be moved at once.",
    "这里的分量太少，搬不开。": "There is too little here to move.",
    "目的地容量不够，搬不过去。": "The destination has no capacity left.",
    "来源存量不足，计划不可执行。": "The source no longer holds enough for this plan.",
    "搬运完成：移动 {moved}，来源剩余 {residual}。":
        "Transfer complete: moved {moved}, {residual} left at the source.",
    "没有可以执行的搬运计划。": "No transfer plan to execute.",
    "落点已经放不下，请重新预览。": "The destination no longer has room; preview again.",
    "（实际移动 {moved}，来源剩 {residual}）":
        " (moved {moved}, {residual} left at the source)",
    # 液气区域（2026-10-18 docs 第 8 节第三批）
    "液态": "liquid", "气态": "gas",
    "一滩": "a pool of ", "一片": "a patch of ", "一池": "a basin of ", "一洼": "a puddle of ",
    "的可见部分": " (visible part)",
    "{span}的{quantifier}{material}{suffix}": "{quantifier}{material} {span}{suffix}",
    "可见 {cells} 格 · 存量 {amount:g}": "visible {cells} cells · volume {amount:g}",
    "{first}至{last}": "{first}–{last}",
    "区域里有受保护的部分，不能一起抹淡。":
        "Part of the region is protected and cannot be thinned together.",
    # 句子最终标点/语序（2026-10-18 docs 第 8 节第一批）
    "你所在的位置也会发出声音": "your own position will also make noise",
    "可这一声没能传出去": "but that sound never gets out",
    "半径内听见的都会径直追来": "everything within the radius that hears it heads straight for you",
    "它仍不会察觉": "it still will not notice",
    "{sentence}，用的是「{name}」的力道": '{sentence}, with the force of “{name}”',
    "{enemy}循声向你走来，可这一声没能传出去。":
        "{enemy} walks toward the sound, but the sound does not carry.",
    # ---- 地图篡改：材料专属字词「点燃 / 浸透」（docs §五/六）----
    "点燃": "Ignite",
    "浸透": "Soak",
    "可燃的墙、植物、气液与地上物会被点着。":
        "Flammable walls, plants, gases, liquids and items on the ground catch fire.",
    "吸水的纤维材质会被水浸透；若目标本身是墙体，完整度再降 10 点（不低于 1）。":
        "Absorbent fibrous material soaks through; if the target is a wall it also loses "
        "10 integrity (never below 1).",
    "这里没有可以点燃的东西。": "There is nothing here that can be set alight.",
    "这个东西太高，水浸不透。": "This is too tall for water to soak through.",
    "这种材质吸不住水。": "This material cannot absorb water.",
    "「{name}」烧了起来。": "{name} catches fire.",
    "这段文字没能点着这里。": "The words fail to set this alight.",
    "水渗进了「{name}」。": "Water seeps into {name}.",
    "〔{name}〕将被点燃": "{name} will be set alight",
    "〔{name}〕将被水浸透": "{name} will be soaked through",
    # ---- 地图篡改面板：条件小节与合并代价预览 ----
    "── 条件 ──": "── Conditions ──",
    "    条件代价：想象力 {sign}{n}": "    Condition cost: Imagination {sign}{n}",
    "    条件代价：混乱 {sign}{n}": "    Condition cost: Chaos {sign}{n}",
    "    效果差异：{note}": "    Difference: {note}",
    "代价：想象力 {a} · 混乱 +{b}": "Cost: Imagination {a} · Chaos +{b}",
    "点击名字或字词选择 · [ ]/,. 换条件 · Enter 执行 · Esc 返回":
        "Click a name or word · [ ]/,. change condition · Enter cast · Esc back",
    "点击或 ↑↓ 选字词 · [ ]/,. 换条件 · Enter 进确认 · Esc 退出":
        "Click or ↑↓ pick a word · [ ]/,. change condition · Enter confirm · Esc exit",
    # ---- 地图篡改面板：目标／字词小节与代价行（2026-10-17 三轮补齐）----
    "── 目标 ──": "── Targets ──",
    "── 字词 ──": "── Words ──",
    "〔{category}〕{label}": "[{category}] {label}",
    "    想象力 {a} · 混乱 +{b}": "    Imagination {a} · Chaos +{b}",
    # ---- 第四轮：条件×关系词、脆裂与强诱引（docs §七）----
    "强诱引": "Strong Lure",
    "这一声不再按距离分档：半径内所有听见的失控意识都会径直追来。":
        "This sound no longer grades by distance: every anomaly that hears it "
        "within the radius comes straight toward the sound.",
    "它还没察觉：会悄悄前往调查，不会先起疑。":
        "It is still unaware: it will investigate quietly instead of growing suspicious first.",
    "，半径内听见的都会径直追来": ", and everything that hears it charges straight in",
    "，它仍不会察觉": ", and it stays unaware",
    "〔{actor}〕循着这句改写，悄悄前往〔{destination}〕调查。":
        "{actor} follows the rewritten words and quietly investigates {destination}.",
    "强诱引的声音从〔{name}〕所在的位置响起，听见的都在径直赶来。":
        "A strong lure rings out from {name}; everything that hears it is charging in.",
    "脆裂": "Brittle Break",
    "结构": "Structure",
    "脆性材质沿裂纹碎开：失去当前完整度的一半；崩塌仍走材料后果。":
        "Brittle material splits along its cracks: it loses half its current "
        "integrity; collapse still follows the material's own consequences.",
    "这种材质不会沿着裂纹碎开。": "This material does not split along cracks.",
    "〔{name}〕将沿着裂纹碎开（失去 {n} 点完整度）":
        "{name} will split along its cracks (loses {n} integrity)",
    "〔{name}〕将沿着裂纹碎开": "{name} will split along its cracks",
    # ---- 第四轮：流体几何字词「泼开 / 扬散」----
    "泼开": "Spill Out",
    "扬散": "Scatter",
    "流向": "Flow",
    "气流": "Airflow",
    "把所选液态记忆的一半摊到相邻可通行格；总量不变，余量保留原有年龄。":
        "Spill half of the chosen liquid memory onto adjacent walkable cells; "
        "the total is conserved and the remainder keeps its age.",
    "把所选弥散印象的一半扬到相邻可流通格；总量不变，余量保留原有年龄。":
        "Scatter half of the chosen diffuse impression into adjacent open cells; "
        "the total is conserved and the remainder keeps its age.",
    "这里的分量太少，摊不开。": "There is too little here to spread.",
    "周围没有可以摊开的格子。": "There are no adjacent cells to spread into.",
    "分量不够分给相邻的格子。": "There is not enough to share with adjacent cells.",
    "〔{name}〕将向相邻格散开一半": "{name} will spread half of itself to adjacent cells",
    "「{name}」向相邻的地面摊开了一半。": "{name} spills half of itself across the ground.",
    "「{name}」向相邻的空间扬散了一半。": "{name} scatters half of itself into the air.",
    # ---- 第五轮：植物拔除与流体聚拢 ----
    "拔除": "Uproot",
    "聚流": "Gather Flow",
    "聚气": "Gather Air",
    "根须": "Roots",
    "把所选植物连根拔起；稀有植物按原拔除口径结算收益。":
        "Tear the chosen plant out by the roots; rare plants pay out under the "
        "same uproot rules as before.",
    "把相邻格的液态记忆收进所选格；总量守恒，混合同格可能当场触发反应。":
        "Draw liquid memory from adjacent cells into the chosen cell; the total is "
        "conserved, and mixing in one cell may trigger a reaction on the spot.",
    "把相邻格的弥散印象收进所选格；总量守恒，混合同格可能当场触发反应。":
        "Draw diffuse impressions from adjacent cells into the chosen cell; the "
        "total is conserved, and mixing in one cell may trigger a reaction on the spot.",
    "这里没有可以拔起的植物。": "There is no plant here to uproot.",
    "相邻没有可以聚拢的东西。": "There is nothing adjacent to gather.",
    "你把「{name}」连根拔起。": "You tear {name} out by the roots.",
    "〔{name}〕将把相邻的流体收拢过来": "{name} will draw the adjacent fluid in",
    "〔{name}〕将被连根拔起": "{name} will be torn out by the roots",
    "「{name}」把相邻的液态记忆聚了过来。": "{name} gathers the adjacent liquid memory in.",
    "「{name}」把相邻的弥散印象聚了过来。": "{name} gathers the adjacent diffuse impressions in.",
    # ---- 第六轮：植物状态 / 液体蒸发与凝固 / 气体沉降 ----
    "催生": "Grow",
    "枯萎": "Wither",
    "蒸发": "Evaporate",
    "凝固": "Solidify",
    "沉降": "Settle",
    "长势": "Growth",
    "干枯": "Withering",
    "形态": "Form",
    "低草长成高丛（遮挡视线）；已经长到头或稀有植物长不动。":
        "Low grass grows into tall clumps (blocking sight); plants already at "
        "their limit or rare plants do not grow.",
    "让植株提前干枯：燃烧时燃料更耐久；植物本身还在。":
        "Wither the plant ahead of time: it burns longer when ignited; the plant itself remains.",
    "把部分液体按它自己的蒸发产物化为气体；不会蒸发的液体给可读拒绝。":
        "Convert part of the liquid into its own evaporation gas; liquids that do "
        "not evaporate get a readable refusal.",
    "把可凝固的液体立成一堵新墙（完整度取墙种定义），液体消失。":
        "Turn a solidifiable liquid into a new wall (integrity from the wall "
        "definition); the liquid disappears.",
    "把部分气体凝回对应的液体；没有沉降产物的气体给可读拒绝。":
        "Condense part of the gas back into its liquid; gases without a settle "
        "product get a readable refusal.",
    "这里没有可以催生的植物。": "There is no plant here that can grow.",
    "这株植物已经长到头了。": "This plant has already grown as far as it will.",
    "这里没有可以枯萎的植物。": "There is no plant here to wither.",
    "这里没有可以蒸发的液体。": "There is no liquid here to evaporate.",
    "这种液体不会自然蒸发。": "This liquid does not evaporate on its own.",
    "这里没有可以凝固的液体。": "There is no liquid here to solidify.",
    "这种液体凝不住。": "This liquid will not set.",
    "分量太少，凝不成一堵墙。": "There is too little to set into a wall.",
    "这里没有可以沉降的气体。": "There is no gas here to settle.",
    "这种气体不会沉下来。": "This gas does not settle out.",
    "分量太少，沉不出东西来。": "There is too little to settle anything out.",
    "〔{name}〕将长高成丛": "{name} will grow into a tall clump",
    "〔{name}〕将提前干枯": "{name} will wither ahead of time",
    "〔{name}〕将按自己的蒸发产物化气": "{name} will evaporate into its own vapour",
    "〔{name}〕将凝成一堵新墙": "{name} will set into a new wall",
    "〔{name}〕将沉降回液体": "{name} will settle back into liquid",
    "「{name}」长高了一截。": "{name} grows taller.",
    "「{name}」提前干枯了——烧起来会更久。":
        "{name} withers ahead of time — it will burn longer.",
    "「{name}」蒸起一缕{gas}。": "{name} gives off a wisp of {gas}.",
    "「{name}」凝成了一堵{wall}。": "{name} sets into a {wall}.",
    "「{name}」沉下一层{liquid}。": "{name} settles out a layer of {liquid}.",
    "以乱代想": "Pay with Chaos",
    "想象力少付 2 点，混乱度多涨 4 点；效果本身不变。":
        "Pay 2 less Imagination and gain 4 more Chaos; the effect itself is unchanged.",
    # 2026-10-22：地表字词三条说明此前只有中文（运行期审计查出的 tab 漏项）。
    "它会立刻发现你，并向你走来。":
        "It will notice you at once and walk straight toward you.",
    "它会被损坏；损坏到头就会塌。":
        "It takes damage; once it is worn through, it collapses.",
    "这个名字会被从眼前抹去。":
        "This name is wiped from sight.",
}
