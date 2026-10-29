"""英文语言包 · 内容分册（由 scripts/_split_i18n_content.py 生成）。

事件、物品包、对话选项标签、征兆再平衡标签、搭桥。
键仍是中文原文；合并进 EN 的顺序见 dream_demo/i18n.py 末尾。
"""

from __future__ import annotations




# ---- 复合事件升级批（2026-09-18）：选项标签 / 对话 / 效果模板 ----
EN_EVENTS_SEP18: dict[str, str] = {
    # 效果模板（面板逐段 tr）
    "离开（不结算）": "Leave (nothing resolved)",
    "获得 {item} ×{n}": "Gain {item} ×{n}",
    "崩解度 +{n}": "Dissolution +{n}",
    "{label} {sign}{n}": "{label} {sign}{n}",
    "无额外结算": "No extra effect",
    # 对话行
    "红字写着：「此处节奏拖沓，建议删去一段。」": "Red ink reads: \"This passage drags; suggest cutting a section.\"",
    "浴缸里的水退向一个不存在的地漏。": "The bathwater drains toward a drain that does not exist.",
    "水面下映出另一个浴室：有人背对着你，在给一个空杯子接水。": "Beneath the surface another bathroom shows: someone, back turned to you, fills an empty cup.",
    "药盒内侧刻着一行小字：「别忘了今天不是星期日。」": "Inside the pill box, tiny letters read: \"Don't forget today isn't Sunday.\"",
    "电台正在念一份名单，每一个名字都停顿两秒，像在等应答。": "The radio reads a list of names, pausing two seconds after each, as if waiting for an answer.",
    "翻到最后一页时，你看见自己的名字写在借阅卡上——归还日期是今天。": "On the last page you find your name on the borrowing card — due back today.",
    "一只由书脊拼成的手把一本书推到你面前。": "A hand pieced together from book spines pushes a book toward you.",
    "你伸手碰到钟壁的瞬间，整片海安静了一拍——它在等一个敲钟人。": "The moment you touch the bell, the whole sea falls silent for a beat — it is waiting for a bellringer.",
    "镜中人比你先抬手。它递来一份没有问题的问卷。": "Your reflection raises its hand first. It hands you a questionnaire with no questions on it.",
    "表格末尾写着：请描述一个你没有做过的梦。": "At the bottom the form reads: describe a dream you have never had.",
    "价签上写着：用一段记得的时间来换。": "The price tag reads: traded for a span of remembered time.",
    "其中一封的信封上写着你的笔迹，但你从不记得写过。": "One envelope bears your own handwriting, yet you never remember writing it.",
    "病历夹上写着你的名字，诊断那一栏被水渍晕开了。": "The chart bears your name; the diagnosis line is blurred by water.",
    "注释写着：只在闭上一只眼时可见。": "The note reads: visible only with one eye closed.",
    "包裹单上寄件人一栏写着「以后的你自己」。": "On the parcel slip, the sender line reads \"your later self\".",
    # 选项标签（按事件分节）
    "拿走那半罐咖啡": "Take the half can of coffee",
    "顺着圆环找路": "Follow the ring's trail",
    "不去动它": "Leave it untouched",
    "拧下那颗螺丝": "Unscrew the last screw",
    "把模型拆开看": "Take the model apart",
    "让它保持完整": "Keep it whole",
    "收下那张票": "Accept the ticket",
    "替它检一次票": "Punch the ticket for it",
    "不理会催促": "Ignore the urging",
    "捡起清醒玻璃": "Pick up the clarity glass",
    "把手贴上玻璃": "Press your hand to the glass",
    "移开视线": "Look away",
    "取出那段机械声": "Take out the mechanical sound",
    "调到没有雨的频率": "Tune to a rainless frequency",
    "由它下着": "Let it rain on",
    "取下那盏灯": "Take the lamp down",
    "让灯照一会儿": "Let it shine a while",
    "关灯离开": "Switch it off and leave",
    "收下空白乐谱": "Take the blank score",
    "在末行补一句": "Add a line at the end",
    "合上它": "Close it",
    "在批注下签名": "Sign beneath the note",
    "把批注涂改成「保留」": "Scribble the note into KEEP",
    "合上稿纸": "Close the manuscript",
    "拾起那枚齿轮": "Pick up the gear",
    "让它再转一圈": "Let it turn once more",
    "保持静止": "Stay still",
    "捡起那只汽笛": "Pick up the whistle",
    "吹响一声": "Blow it once",
    "把手收回来": "Draw your hand back",
    "伸手进漩涡": "Reach into the whirlpool",
    "对着水中的人说话": "Speak to the figure in the water",
    "拔掉不存在的塞子": "Pull the nonexistent plug",
    "吃掉剩下的药": "Take the remaining pills",
    "把整盒收进口袋": "Pocket the whole box",
    "原样合上": "Close it as it was",
    "捞起那张乐谱": "Fish out the score",
    "按住那个休止符": "Hold down the rest",
    "让它继续泡着": "Let it keep soaking",
    "带走空心的台阶": "Take the hollow step",
    "顺着梯子爬上去": "Climb the ladder",
    "收回梯子": "Fold the ladder back",
    "取下那扇窗": "Take the window down",
    "看站台慢慢落后": "Watch the platform fall behind",
    "拉上窗帘": "Draw the curtain",
    "报上自己的名字": "Speak your name",
    "跟着电流声哼下去": "Hum along with the static",
    "关掉电台": "Turn off the radio",
    "收起那把卷尺": "Pocket the tape measure",
    "拉到底再画一条": "Stretch it and draw another",
    "不量了": "Stop measuring",
    "接过那本书": "Take the book",
    "把名字从借阅卡上擦掉": "Erase your name from the card",
    "轻轻放回，退出图书馆": "Put it back and slip away",
    "接住那滴晨露": "Catch the drop of dew",
    "对着深渊听回声": "Call into the abyss and listen",
    "退出这片寂静": "Leave the silence",
    "撞响它": "Strike the bell",
    "把耳朵贴上去听": "Press your ear to it",
    "松手，让钟继续沉睡": "Let go; let it sleep on",
    "取下无光灯笼": "Take the lightless lantern",
    "在标题下签名": "Sign beneath the title",
    "把画翻过去": "Turn the painting to the wall",
    "捞起那杯茶": "Fish out that cup of tea",
    "念出一个名字": "Speak a name aloud",
    "等潮水退去": "Wait for the tide to recede",
    "如实填写": "Fill it in truthfully",
    "交白卷": "Hand in a blank sheet",
    "打碎镜子离开": "Shatter the mirror and leave",
    "留下一段记忆换表": "Leave a memory for a watch",
    "把所有表拨到四点": "Set every watch to four",
    "什么都不碰": "Touch nothing",
    "拆开那封自己写的信": "Open the letter in your own hand",
    "把所有信投进不存在的邮筒": "Post every letter into the nonexistent box",
    "信还是让它泡着吧": "Let the letters soak",
    "按铃叫护士": "Ring for the nurse",
    "替自己写下出院医嘱": "Write your own discharge note",
    "轻轻带上门": "Close the door softly",
    "闭上一只眼找它": "Shut one eye and find it",
    "把那颗星涂掉": "Blot out that star",
    "合上抽屉": "Close the drawer",
    "签收包裹": "Sign for the parcel",
    "写一封投给过去的信": "Write a letter to the past",
    "把包裹留在柜台上": "Leave the parcel on the counter",
    "拿走那点温水": "Take the pool of warm water",
    "投一枚硬币下去": "Drop in a coin",
    "留它们朝上": "Leave them heads-up",
    "带走空心台阶": "Take the hollow step",
    "等音乐放完": "Wait for the music to finish",
    "按开门键": "Press the door-open button",
    "取走那卷底片": "Take the roll of film",
    "再拍一张": "Take one more shot",
    "从逆光的底片中取出裁纸刀": "Take the paper cutter from the backlit negative",
    "反扣的接地腕带沿导电介质接通了 {n} 格电场。":
        "The reversed grounding band charged {n} conductive cells.",
    "走出幕布": "Step out of the curtain",
    "取下那只挂钩": "Take the hook down",
    "推一推铰链印子": "Push at the hinge marks",
    "关上柜门": "Close the wardrobe door",
}

# ---- 内容扩展包 v1 Phase B：装备/洞察/构想 ----
EN_ITEMS_PACK_V1: dict[str, str] = {
    "火花": "Spark",
    "望远": "Farsight",
    "冻凝": "Frost Touch",
    "烟幕": "Smoke Veil",
    "迟缓": "Slow Wave",
    "冲印": "Develop",
    "回响": "Echo Pulse",
    "推斥": "Repulse",
    "镜面": "Mirror Stance",
    "曝光": "Blur",
    "引爆": "Detonate",
    "火墙": "Firewall",
    "烈焰新星": "Flame Nova",
    "生锈的美工刀": "Rusty Boxcutter",
    "推出来回拉的钝刀，胜在随手可得。": "A blade that only retracts — but it's always at hand.",
    "长尾夹发射器": "Binder-Clip Launcher",
    "绷紧的金属夹带着轻微穿透射出去。": "Fires a sprung metal clip with slight penetration.",
    "录音笔": "Voice Recorder Pen",
    "发射即广播：弹着点的声波把异象引向别处。": "Firing it is a broadcast: the impact's sound pulls anomalies elsewhere.",
    "裂开的放大镜": "Cracked Focusing Lens",
    "聚成一线的光：命中点燃目标格的可燃物。": "Light focused to a line: hits ignite flammables on the target tile.",
    "梦貘鼻烟壶": "Dream-Tapir Snuffbox",
    "命中三成概率让对方直接睡去。": "30% chance on hit to put the target straight to sleep.",
    "节拍摆刃": "Metronome Blade",
    "跟着节拍出手：又快又狠。": "Strikes on the beat: fast and hard.",
    "没水的笔": "Dry Pen",
    "一笔划掉：命中两成概率直接删去对方身上的征兆。": "One stroke to erase: 20% chance on hit to delete a portent from the target.",
    "打蜡的雨衣": "Waxed Raincoat",
    "液体接触的负面征兆对你减半。": "Harmful portents from liquid contact are halved for you.",
    "铅衬里的围裙": "Lead-Lined Apron",
    "心智创伤 −2、清醒创伤 −2。": "Mind damage −2, lucidity damage −2.",
    "静电披风": "Static Poncho",
    "受击时向相邻的攻击者反打一记传导冲击。": "When struck, shocks back any adjacent attacker.",
    "停摆的节拍器": "Stopped Metronome",
    "攻击耗时 −0.1：攻速流的核心小件。": "Attacks cost −0.1 time: the core of a speed build.",
    "刻度磨损的指南针": "Worn Surveyor's Compass",
    "悬停读数额外显示到目标的最短步数。": "Hover readouts also show the shortest step count to the target.",
    "压扁的四叶草": "Flattened Four-Leaf Clover",
    "崩解度获取 +4：滚雪球型收益。": "Dissolution gain +4: a snowballing trinket.",
    "绝缘手套": "Insulated Gloves",
    "徒手操作机关与电线不再触发反噬。机关流必备。": "Handle mechanisms and wires bare-handed without backlash. Essential for contraption builds.",
    "多功能军刀": "Multitool Knife",
    "修缮 +50：装备更耐用。": "Repairs +50: your gear lasts longer.",
    "听诊器": "Stethoscope",
    "隔墙一格也能听到异象的轮廓。": "Hear anomaly outlines through one tile of wall.",
    "电工直觉": "Electrician's Intuition",
    "你能看见电线：机关与陷阱石台之间的无形连线以虚线显形。": "You can see wires: the invisible links between mechanisms and trap tables show as dashed lines.",
    "机关嗅觉": "Nose for Mechanisms",
    "陷阱石台在悬停读数里多一行灰色警示，无需拆除即可趋避。": "Trap tables gain a grey warning line in hover readouts — avoid them without dismantling.",
    "守株待兔": "Waiting by the Stump",
    "原地等待后，你的下一次攻击创伤 +2。": "After waiting in place, your next attack deals +2 damage.",
    "地形记忆": "Terrain Memory",
    "已显影的地形在本层内永久保留，不再因低清醒度丢失。": "Developed terrain stays revealed for the whole layer, never lost to low lucidity.",
    "读唇": "Lip Reading",
    "会说话的异象在视野内时，你能读出它下一步的移动意图。": "Talkative anomalies in sight reveal their next intended step.",
    "无声步": "Soundless Step",
    "你移动产生的声音半径 −1（最低 1）。": "Sounds from your movement carry −1 radius (min 1).",
    "夜行惯性": "Nocturnal Momentum",
    "连续移动 6 回合后，第 7 回合移动不耗时。": "After 6 consecutive moves, the 7th move costs no time.",
    "伤口结痂": "Scabbing",
    "单次受到创伤 ≥9 时，超出 9 点的部分减半。": "Wounds of 9 or more: the excess over 9 is halved.",
    "深渊回声": "Abyssal Echo",
    "在无意识领域，你的声波脉冲额外传 2 格。": "In the Unconscious, your sound pulses carry 2 extra tiles.",
    "短路": "Short Circuit",
    "强制触发视野内任意一个逻辑固体，无论条件是否满足。": "Force-trigger any logic solid in sight, conditions or not.",
    "接线": "Rewire",
    "改接一条电线：把一个触发源的输出改指到另一个可触发物体。": "Rewire a line: point one trigger's output at a different receiver.",
    "凝滞": "Stasis",
    "立即冻结自身 3 个世界回合（含施放回合）：免疫创伤与征兆，不能执行行动；仍可查看、取消、等待和保存。": "Immediately enter stasis for 3 world rounds, including the casting round. Immune to harm and portents; actions are blocked, but inspecting, cancelling, waiting and saving remain available.",
    "匿踪": "Vanish",
    "3 回合内对异象完全隐身（不触发警戒）。": "Fully invisible to anomalies for 3 rounds (no alerts).",
    "回闪": "Flashback",
    "回到 3 回合前所在的那一格（若仍可通行）。": "Return to the tile you occupied 3 rounds ago (if still passable).",
    "火种": "Kindle",
    "在面朝格及其四邻种下一圈火（十字 5 格），引燃可燃物与气体。": "Plant a ring of flame on the facing tile and its four neighbors (a 5-tile cross), igniting flammables and gases.",
    "共鸣": "Resonance",
    "与一件携带意象共鸣：其效果 ×1.5，持续 8 回合。": "Resonate with one carried item: its effect ×1.5 for 8 rounds.",
    "梦魇燃料": "Nightmare Fuel",
    "以 5 点清醒度为代价，回复想象力上限的 40%（四舍五入）。": "Pay 5 lucidity to restore 40% of your max imagination (rounded).",
    "凝露": "Condense Dew",
    "在相邻一格生成 24 点水：灭火、导电、稀释、喂纸鱼。": "Create 24 water in an adjacent tile: douse, conduct, dilute, feed paper fish.",
    "播绿": "Sow Green",
    "在面朝格周围半径 2 播下一片低草：掩体与植物联动的种子。": "Sow low grass within radius 2 of the facing tile: cover, and seeds for plant synergies.",
    "蜡封": "Wax Seal",
    "把脚下或相邻一格封成蜡化记忆墙（完整度 45，可徒手破坏）。": "Seal your own or an adjacent tile into a wax wall (45 integrity, breakable by hand).",
    "汲引": "Draw Liquid",
    "吸干近旁 2 格内最近一格的全部液体，转化为 2 点想象力。": "Drain all liquid from the nearest tile within 2 steps, converting it into 2 imagination.",
    "冰桥": "Ice Bridge",
    "把近旁 2 格内的液体格冻结成可滑行的冰面地板，造路穿越液区。": "Freeze liquid tiles within 2 steps into slippery ice — a road across the pool.",
    "蒸腾": "Transpire",
    "把近旁 2 格内最近一格液体原地化为对应的气体。": "Turn the nearest liquid tile within 2 steps into its corresponding gas.",
    "融蚀": "Dissolve Wall",
    "溶解相邻一面硬度 ≤6 的墙；硬墙（致密/梦魇岩）无效。": "Dissolve an adjacent wall of hardness ≤6; hard walls resist.",
    "隆起": "Raise Ground",
    "抬升目标 5×5 的地势（+1 档）：液体将流走，造出高地。": "Raise a 5×5 area one step: liquids drain away — a dry highland.",
    "陷落": "Sink Ground",
    "使目标 5×5 地势下陷（−1 档）：造洼地引液体、挖陷阱坑。": "Lower a 5×5 area one step: dig a basin to draw liquids and set traps.",
    "崩落": "Collapse",
    "目标走廊两侧的墙向内坍塌一格，生成碎屑堆堵住通道。": "Walls on both sides of a corridor cave in one tile, blocking it with rubble.",
    "凝聚": "Conjure Wall",
    "在相邻空格凭空凝聚一面臆造聚合墙（可破坏、可推）。": "Conjure a polymer wall on an adjacent tile (breakable, pushable).",
    "重写一隅": "Rewrite a Corner",
    "以目标格为中心 7×7 的地形被梦境当场重写——可能把好事改坏。": "A 7×7 area is rewritten by the dream on the spot — it may just as easily turn bad.",
}

# ---- 事件对话与选项标签（2026-10-07 补齐：i18n 测试此前只查事件名/描述，
# dialogue 与 options[].label 整批漏翻，英文模式下事件面板全程中文）----
EN_EVENTS_DIALOGUE_LABELS: dict[str, str] = {
    "✦ 随机易逝物（稀有度随机）": "✦ Random ephemeral (random rarity)",
    "✦ 随机摄入物（稀有度随机）": "✦ Random ingestible (random rarity)",
    "✦ 随机携带意象（稀有度随机）": "✦ Random carried image (random rarity)",
    "有一张的背面写着：别回头，继续走。":
        "On the back of one, a note: Don't look back. Keep walking.",
    "揭一张带走": "Peel one off and take it",
    "在墙前站一会儿": "Stand before the wall a while",
    "全部撕下来": "Tear them all down",
    "不去看它们": "Don't look at them",
    "渗出的水在你脚边汇成一小片浅洼。":
        "The seeping water gathers into a shallow puddle at your feet.",
    "用玻璃瓶接一瓶": "Fill the glass bottle with it",
    "对着滴答声发呆": "Stare blankly at the ticking",
    "把水龙头拧紧": "Twist the faucet shut",
    "表盘上贴着便签：「别让它停下来。」":
        "A sticky note on the dial: \"Don't let it stop.\"",
    "拆下电池": "Take the battery out",
    "陪它转到停": "Sit with it until it stops",
    "合上电表箱": "Close the meter box",
    "折痕把月面分成了四格，每一格都在慢慢鼓起来。":
        "Creases divide the moon into four panels, each slowly swelling.",
    "戳破它": "Poke it open",
    "把折痕抚平": "Smooth out the creases",
    "锁是开的，它在邀请你。": "The lock is open. It is inviting you.",
    "翻找易逝物": "Search for ephemerals",
    "替它守一会儿": "Keep watch over it a while",
    "走开": "Walk away",
    "「雨」音栓被按下了，所以才有这层雾。":
        "The \"Rain\" stop is pressed down — that is why the fog is here.",
    "按下「晴」音栓": "Press the \"Clear\" stop",
    "即兴弹一段": "Improvise a passage",
    "悄悄退出去": "Slip quietly out",
    "抽屉里的东西比你记忆中多了一倍。":
        "The drawer holds twice as much as you remember.",
    "一杯一杯地喝": "Drink it cup by cup",
    "把抽屉关好": "Close the drawer properly",
    "信一格一格往下掉，落进醒来的世界。":
        "Letters drop cell by cell, falling into the waking world.",
    "寄一份礼物给醒着的自己": "Mail a gift to your waking self",
    "读别人的来信": "Read someone else's mail",
    "什么也不寄": "Send nothing",
    "墓志铭：「它修好过一切，除了它自己。」":
        "Epitaph: \"It fixed everything but itself.\"",
    "取走扳手墓碑": "Take the wrench headstone",
    "向工具箱致意": "Salute the toolbox",
    "添一撮土再离开": "Add a pinch of soil, then leave",
    "每倒退一格，空气里的咸味就重一分。":
        "With every tick backward, the salt in the air grows heavier.",
    "把指针拨向涨潮": "Push the hand toward high tide",
    "把指针拨向退潮": "Push the hand toward low tide",
    "让潮水自己决定": "Let the tide decide",
    "镜子里的你在反复排练一句台词。":
        "The you in the mirror is rehearsing one line, over and over.",
    "它排练得比你认真多了——认真到忘了词就会重头再来。":
        "It rehearses far more earnestly than you — earnest enough to start over the moment it forgets a word.",
    "陪它排练一遍": "Rehearse with it once",
    "抢过它的台词": "Steal its line",
    "安静等它念完": "Wait quietly for it to finish",
    "指挥转过头——它没有脸，只有一圈静电。":
        "The conductor turns — it has no face, just a ring of static.",
    "跟着哼一段": "Hum along for a while",
    "录下这段调音": "Record this tuning",
    "捂住耳朵快走": "Cover your ears and hurry off",
    "雨从地面升回云端。": "The rain climbs back from the ground into the clouds.",
    "接住一滴，它会在掌心重演整场雨季。":
        "Catch one drop and it will replay the whole rainy season in your palm.",
    "接一滴": "Catch a drop",
    "在雨里站一会儿": "Stand in the rain a while",
    "躲开": "Dodge away",
    "走廊两侧的门越走越多。": "The doors along both sides multiply as you walk.",
    "每一扇门后还是这走廊——只有门把手温度不同。":
        "Behind every door is this same corridor — only the handles' warmth differs.",
    "敲敲最旧的那扇": "Knock on the oldest door",
    "把耳朵贴在门上听": "Press your ear to a door and listen",
    "原路返回": "Turn back the way you came",
    "蜡化的客人们围坐一桌，姿势保持着举杯。":
        "Wax-melted guests sit around a table, frozen mid-toast.",
    "茶壶还在倒——倒出的蜡在杯里堆成小山。":
        "The teapot still pours — the wax piles up in the cups like little hills.",
    "入席陪一杯": "Take a seat and share a cup",
    "向客人们行礼": "Bow to the guests",
    "不打扰了": "Leave them undisturbed",
    "每一页落地前都闪过一段你没写完的段落。":
        "Before each page lands, it flashes a paragraph you never finished.",
    "把碎片拼回去": "Piece the fragments back together",
    "接住飘落的一页": "Catch a falling page",
    "让书继续撕": "Let the book keep tearing",
    "稿子里提到的街道你全都认识——只是每条都少了路灯。":
        "You know every street in the script — only the streetlights are missing.",
    "给电台拨个电话": "Call the station",
    "跟着念最后一段": "Read the last paragraph along with it",
    "关掉喇叭": "Switch off the speaker",
    "一把椅子朝你游过来，像在邀请你下水。":
        "A chair swims toward you, as if inviting you into the water.",
    "下水陪它们游": "Join them in the water",
    "把家具捞上岸": "Fish the furniture ashore",
    "站在门口看": "Watch from the doorway",
    "摊主不在，摊位上只剩最后一颗样品。":
        "The stall keeper is gone; only the last sample remains on display.",
    "买下最后一颗样品": "Buy the last sample",
    "帮摊主看一会儿摊": "Mind the stall for a while",
    "不买": "Don't buy",
    "戏名写在幕布上：《等一个剪断我们的人》。":
        "The play's name is on the curtain: \"Waiting for Someone to Cut Our Strings.\"",
    "剪断一个木偶的线": "Cut one puppet's strings",
    "为他们鼓掌": "Applaud them",
    "悄悄退场": "Slip out of the show",
    "玻璃瓶立在门扉边——瓶塞上刻着一行小字：打开我。":
        "A glass bottle stands by the door — tiny words carved on the cork: Open me.",
    "抱走玻璃瓶": "Carry the glass bottle off",
    "贴耳听瓶中的水声": "Listen to the water inside the bottle",
    "气球拴在门把手上，皮面随着你的呼吸微微鼓动。":
        "A balloon is tied to the door handle, its skin swelling faintly with your breath.",
    "解下气球": "Untie the balloon",
    "放它飞走": "Let it fly away",
    "离开": "Leave",
    "深潜裂隙": "Deep-Dive Rift",
    "初啼之核崩解处裂开一道向下的缝。深处有写字的声音。":
        "Where the First-Cry core dissolved, a seam has cracked open, leading down. From the depths comes the sound of writing.",
    "裂隙里透上来的不是光，是更深的黑。黑里有笔尖划纸的沙沙声。":
        "What seeps from the rift is not light but a deeper dark. Inside the dark, a pen nib whispers across paper.",
    "跳下去，就能找到那个「写字的人」。或者，就此醒来。":
        "Jump, and you will find the \"one who writes.\" Or wake up here and now.",
    "就此醒来（结局：初醒）": "Wake up now (ending: First Waking)",
    "深潜（清醒 -8，进入深层边界）": "Deep dive (clarity −8, enter the Deep Boundary)",
}

# ---- 2026-10-07 核心循环改版：征兆分级 / 深度函数 / 附着层 的新描述与消息 ----
EN_PORTENT_REBALANCE_LABELS: dict[str, str] = {
    "扬尘": "Dust Cloud",
    "隐隐发烫的赤色地面：余温烘得本格液体多蒸掉 2 点、气体多散 1 点；站上每 3 回合清醒 −1（2026-10-07 起有微量战斗读数）；不造成伤害、不影响行走；总是成片铺开。":
        "A faintly hot crimson floor: leftover warmth evaporates 2 more liquid and disperses 1 more gas each interval; standing on it costs 1 lucidity every 3 rounds (a slight combat readout since 2026-10-07); deals no damage and never impedes walking; always spreads in patches.",
    "残余电流在意识里打转：每 2 回合清醒度 −1（随深度 ×1～×2.5，向上取整）；与静电尘同处时每回合额外 −1。":
        "Residual current spins through the mind: lucidity −1 every 2 rounds (×1–×2.5 by depth, rounded up); standing in static dust drains 1 more each round.",
    "镇静溶液压住了惊惶：持续期间环境不再侵蚀心智（毒气/腐蚀/燃烧/下潜反噬等；异象的创伤仍作数）。":
        "Sedative solution holds the panic down: environmental mind loss is blocked (gas/corrosion/burning/descent backlash; anomaly trauma still lands).",
    "酸蚀液仍在啃噬你的意识：每回合失去 1 点心智（随深度 ×1～×2.5，向上取整）。":
        "The acid keeps gnawing at your mind: −1 mind each round (×1–×2.5 by depth, rounded up).",
    "稀释记忆的余温：持续期间每 2 回合恢复 1 点想象力（随深度 ×1～×2.5，向上取整）。":
        "The diluted memory's warmth: +1 imagination every 2 rounds while it lasts (×1–×2.5 by depth, rounded up).",
    "泪滴溶液托住心智：滞留时每回合恢复 1 点心智（随深度 ×1～×2.5，向上取整），每层上限 5。":
        "Tear solution cradles the mind: +1 mind each round while it lingers (×1–×2.5 by depth, rounded up), cap 5 per layer.",
    "水蒸气润开了想象：每 3 回合恢复 1 点想象力（随深度 ×1～×2.5，向上取整）。":
        "Steam loosens the imagination: +1 imagination every 3 rounds (×1–×2.5 by depth, rounded up).",
    "毒气渗进意识：每 2 回合失去 1 点心智（随深度 ×1～×2.5，向上取整）。":
        "Poison gas seeps into the mind: −1 mind every 2 rounds (×1–×2.5 by depth, rounded up).",
    "酒气熏得意识发飘：每 4 回合清醒度 −1（随深度 ×1～×2.5，向上取整），攻击额外耗时 +0.3。":
        "Fumes leave the mind adrift: lucidity −1 every 4 rounds (×1–×2.5 by depth, rounded up), attacks +0.3 time.",
    "酒精蒸气熏得更透：每 2 回合清醒度 −1（随深度 ×1～×2.5，向上取整），攻击额外耗时 +0.5；身上残留的可燃蒸气依然见火就着。":
        "Spirits soak in deeper: lucidity −1 every 2 rounds (×1–×2.5 by depth, rounded up), attacks +0.5 time; the flammable vapors still catch at the first flame.",
    "灰尘塞住视野：每 3 回合清醒度 −1（随深度 ×1～×2.5，向上取整），视野 −1。":
        "Dust clogs the view: lucidity −1 every 3 rounds (×1–×2.5 by depth, rounded up), vision −1.",
    "灼热蒸汽烫着意识：每 2 回合清醒度 −1（随深度 ×1～×2.5，向上取整）。":
        "Scalding steam sears the mind: lucidity −1 every 2 rounds (×1–×2.5 by depth, rounded up).",
    "静电让四肢发木：移动额外耗时 +0.5。":
        "Static numbs the limbs: movement takes +0.5 extra time.",
    "流动月光替你照亮四周：视野 +4（固定值，2026-10-07 由翻倍改为定值）。":
        "Flowing moonlight lights your surroundings: vision +4 (fixed value; was doubling before the 2026-10-07 rebalance).",
    "看见所有意象的位置与形态——每个失控意识的位置与种类都如实显形（连伪装也看穿），代价是它们也同时看见了你的位置，且灵视的通道是双向的：你的声响同样传得更远（声音半径 ×2）。":
        "You see every image's position and form — each rogue consciousness shown true (disguises pierced). The cost: they all see you too, and the channel runs both ways — your own sounds travel twice as far (sound radius ×2).",
    "蜂蜜裹住伤口：每 2 回合恢复 1 点清醒度（随深度 ×1～×2.5，向上取整，每层上限 6）；上方生物移速减半。":
        "Honey seals the wound: +1 lucidity every 2 rounds (×1–×2.5 by depth, rounded up, cap 6 per layer); creatures above move at half speed.",
    "辐射尘埃在体内堆积：每 3 回合心智与清醒度各 −1（随深度 ×1～×2.5，向上取整）。铅板邻格可屏蔽。":
        "Radiation dust accumulates in the body: −1 mind and −1 lucidity every 3 rounds (×1–×2.5 by depth, rounded up). Adjacent lead plates shield you.",
    "特浓薄荷茶提神醒脑：持续期间每 2 回合恢复 1 点清醒度（随深度 ×1～×2.5，向上取整）。":
        "Strong mint tea clears the head: +1 lucidity every 2 rounds while it lasts (×1–×2.5 by depth, rounded up).",
    "咖啡因气让移速提升一半，并免疫深眠与醉意；代价是兴奋烧掉清醒——每 3 回合 −1。":
        "Caffeine gas quickens movement by half and grants immunity to deep sleep and drunkenness; the excitement burns lucidity — −1 every 3 rounds.",
    "梦的边缘在啃食意识：每 2 回合心智 −1（随深度 ×1～×2.5，向上取整）。":
        "The dream's edge gnaws at the mind: −1 mind every 2 rounds (×1–×2.5 by depth, rounded up).",
    "噩梦纤维缠上意识：每 2 回合心智 −1（随深度 ×1～×2.5，向上取整）。":
        "Nightmare fibers coil around the mind: −1 mind every 2 rounds (×1–×2.5 by depth, rounded up).",
    "噩梦气息渗进意识：每 2 回合心智 −1（随深度 ×1～×2.5，向上取整）。":
        "Nightmare breath seeps into the mind: −1 mind every 2 rounds (×1–×2.5 by depth, rounded up).",
    "原初混沌持续冲刷意识：每回合心智 −2（随深度 ×1～×2.5，向上取整）。":
        "Primordial chaos keeps washing through the mind: −2 mind each round (×1–×2.5 by depth, rounded up).",
    "熔念金属在意识里烧出沟壑：每回合清醒 −1（随深度 ×1～×2.5，向上取整）。":
        "Molten-metal thoughts burn grooves into the mind: −1 lucidity each round (×1–×2.5 by depth, rounded up).",
    "星辉露在意识里亮成一片：每 2 回合心智 +1（随深度 ×1～×2.5，向上取整）。":
        "Starlight dew glows across the mind: +1 mind every 2 rounds (×1–×2.5 by depth, rounded up).",
    "雏菊的香气托住念头：持续期间一切心智流失减半（含异象创伤）。":
        "The daisy's scent holds your thoughts: all mind loss is halved while it lasts (including anomaly trauma).",
    "虚无孢子糊住了感官：视野 −4，每 3 回合想象力 −1（随深度 ×1～×2.5，向上取整）。":
        "Void spores smear the senses: vision −4, −1 imagination every 3 rounds (×1–×2.5 by depth, rounded up).",
    "溶梦酸雾把你溶进梦里：每 2 回合清醒 −1（随深度 ×1～×2.5，向上取整），崩解 +1。":
        "Dream-dissolving acid fog melts you into the dream: −1 lucidity every 2 rounds (×1–×2.5 by depth, rounded up), dissolution +1.",
    "晨霜清气提着精神：每 3 回合清醒 +1（随深度 ×1～×2.5，向上取整）。":
        "Morning-frost air braces the spirit: +1 lucidity every 3 rounds (×1–×2.5 by depth, rounded up).",
    "夜皇后的幽光替你照亮四周：视野 +4（固定值，2026-10-07 由翻倍改为定值）。":
        "The Night Queen's ghost-light lights your surroundings: vision +4 (fixed value; was doubling before the 2026-10-07 rebalance).",
    "黏液导电又拉丝：移动额外耗时 +0.6。":
        "The slime conducts and stretches: movement takes +0.6 extra time.",
    "陈年档案的灰呛进肺里：每 3 回合清醒 −1（随深度 ×1～×2.5，向上取整）、视野 −1。":
        "Archive dust catches in the lungs: lucidity −1 every 3 rounds (×1–×2.5 by depth, rounded up), vision −1.",
    "门槛的泪水浸湿鞋底：想象力每 4 回合 +1（随深度 ×1～×2.5，向上取整）。":
        "The threshold's tears soak your soles: +1 imagination every 4 rounds (×1–×2.5 by depth, rounded up).",
    "没水的笔一划——{target}身上的「{name}」被删掉了。":
        "The dry pen strikes — \"{name}\" is erased from {target}.",
    "灼热聚合物透过鞋底炙烤着意识：清醒度 −1。":
        "The scorching polymer bakes through your soles: lucidity −1.",
    "命中两成概率让对方直接睡去。":
        "20% chance on hit to put the target straight to sleep.",
    "一笔划掉：命中两成概率删去对方最近获得的一条征兆。":
        "Strike it out: 20% chance on hit to erase the target's most recently gained portent.",
}

# 构筑桥接组件（2026-10-08，平衡方案 §6.1 的六种原型各补一环）。
EN_BUILD_BRIDGE: dict[str, str] = {
    # ---- 物品名与描述 ----
    "三棱镜的吊坠": "Prism Pendant",
    "吊坠里折射过一次的光不肯回原路：弹体经跳弹改向后命中，给它刻上折射印记（3 回合）。下一次从别的方向打它，创伤 +2，印记随即消耗。":
        "Light that bounced once inside the pendant refuses to return the way it came: a ricochet hit brands the target with a refracted mark (3 rounds). Strike it from another direction next and the blow deals +2 damage, spending the mark.",
    "浸盐的线圈": "Salt-Soaked Coil",
    "盐把水记得很牢：你的放电在湿润目标之间多传一次——2 格内另一位浸在导电液态记忆里的意识吃 2 点完整度，每 6 回合只传得出这一次。":
        "Salt remembers water well: your discharge leaps once more between soaked targets — another consciousness steeped in conductive liquid memory within 2 tiles loses 2 integrity. Only one hop per 6 rounds.",
    "余烬跟的靴子": "Ember-Heeled Boots",
    "鞋跟烧成灰烬也不着：每层你第一次亲手点燃什么时，白得一步免费移动，3 格内正追着你的意识当场跟丢。":
        "The heels char to ash yet never catch: the first thing you personally ignite on each layer earns a free step of movement, and any consciousness chasing you within 3 tiles loses your trail on the spot.",
    "追味的皮绳": "Scent-Tracking Lanyard",
    "绳结记住了材料的气味：身上还挂着附着征兆的意识，你的攻击创伤 +1（不随件数叠加），并说出它附着的是什么。":
        "The knots remember what materials smell like: attacks against a consciousness still carrying an adhered portent deal +1 damage (does not stack across items), and the lanyard names what clings to it.",
    "分岔的音叉": "Bifurcated Tuning Fork",
    "两根齿各自共鸣：一次成功的声波引诱替你把下一次脉冲变成控制——声源 3 格内的意识当场震停 1 回合。武装只在本层有效，跨层作废。":
        "Its two tines resonate separately: one successful sonic lure turns your next pulse into control — consciousnesses within 3 tiles of the source freeze rigid for 1 round. The arming only holds for this layer; descending voids it.",
    "半页空稿": "Half a Blank Page",
    "没写过的那半页肯替你垫付：想象力归零时仍可展开一项构想，免掉它的想象成本（每层一次，冷却与行动时间照常）。洞察「留白」与它共用这一次。":
        "The unwritten half-page gladly covers your debt: with imagination at zero you may still unfold one conception, its imagination cost waived (once per layer; cooldown and action time still apply). Shares that single use with the Blank Space insight.",
    "未装订的书页": "Unbound Page",
    "这一页还没归进任何书里。折痕深处，藏着另一种读法。":
        "This page has never been filed into any book. Deep in its creases hides another way of reading.",
    # ---- 图鉴「作用」与「作用说明」 ----
    "折射印记": "Refracted Mark",
    "潮润传导": "Tidal Conduction",
    "灰烬撤步": "Ashen Retreat",
    "附着追猎": "Adhesion Hunt",
    "回声控场": "Echo Control",
    "留白免单": "Blank-Page Waiver",
    "携带后，弹体经跳弹改向后命中会刻上折射印记（3 回合）；下一次从不同方向命中同一目标额外 +效力 创伤，印记随即消耗。":
        "While equipped, a projectile hit that arrives after a ricochet brands a refracted mark (3 rounds); the next hit on that target from a different direction deals +power extra damage and spends the mark.",
    "你的放电（导电液态记忆、压电地板）在湿润目标之间多传一次：2 格内另一位浸在导电液态记忆里的意识受 效力 点完整度，每 6 回合限一次。":
        "Your discharges (conductive liquid memory, piezo floors) hop once more between soaked targets: another consciousness steeped in conductive liquid memory within 2 tiles loses power integrity, limited to once per 6 rounds.",
    "每层第一次由你亲手点燃时：获得 1 次免费移动，3 格内处于「追踪」的意识降为「怀疑」。":
        "On the first thing you personally ignite each layer: gain 1 free move, and any consciousness within 3 tiles in the Chasing state drops to Suspicious.",
    "对身上仍挂着材料附着的意识，攻击创伤 +1（多件不叠加）；首次命中会报出它附着的是哪种材料。":
        "Attacks against a consciousness still carrying material adhesion deal +1 damage (no stacking across items); the first hit names which material clings to it.",
    "一次成功的声波引诱（有意识循声而去）会武装本层的下一次脉冲：声源 3 格内的意识当场震停 1 回合；武装跨层作废。":
        "One successful sonic lure (a consciousness following the sound) arms this layer's next pulse: consciousnesses within 3 tiles of the source freeze rigid for 1 round. Descending voids the arming.",
    "想象力为 0 时仍可展开一项已习得构想，免除它的想象成本（每层一次；冷却与行动时间照常）。与洞察「留白」共用这一次。":
        "With imagination at 0 you may still unfold one learned conception, its cost waived (once per layer; cooldown and action time still apply). Shares that use with the Blank Space insight.",
    "想象力归零时，每层可免费展开一项已习得的构想（与半页空稿共用这一次）。":
        "With imagination at zero, one learned conception unfolds for free each layer (this single use is shared with Half a Blank Page).",
    # ---- 结算提示 ----
    "折射印记刻在{target}身上（{turns} 回合）：换个方向打它。":
        "A refracted mark is branded onto {target} ({turns} rounds): hit it from another direction.",
    "角度换了——折射印记亮起来，这一击 +{bonus}。":
        "The angle changed — the refracted mark flares, this blow gains +{bonus}.",
    "皮绳认出了味道：{target}身上附着的是「{name}」。":
        "The lanyard catches the scent: {target} is coated in \"{name}\".",
    "音叉有一根齿记下了这次声响——下一次脉冲会带上控制。":
        "One tine of the fork recorded this sound — your next pulse will carry control.",
    "音叉的另一次分岔落下：声源 {radius} 格内 {frozen} 个失控意识当场震停。":
        "The fork's other tine falls: {frozen} rogue consciousnesses within {radius} tiles of the source freeze rigid on the spot.",
    "盐把电流接了过去：湿润的{enemy}也被咬了一口。":
        "Salt carries the current through: the soaked {enemy} takes a bite of it too.",
    "靴跟的余烬散成灰：白得一步，{lost} 个追着你方向的失控意识跟丢了你。":
        "The embers in your heels crumble to ash: a step for free, and {lost} rogue consciousnesses chasing your direction lose your trail.",
    "空着的那半页替你把成本垫上了——这一次不花想象力。":
        "The blank half-page covers the cost for you — this one spends no imagination.",

    # ---- 梦中梦支线·余烬廊桥与退潮厅（2026-10-08）----
    # 位面名
    "余烬廊桥": "Ember Bridge",
    "退潮厅": "Ebbing Hall",
    # 入口 NPC：引火人
    "引火人": "The Lighter",
    "蹲在一堆冷灰边的瘦长身影，手里反复擦着一根擦不着的火柴。":
        "A lanky figure crouched by a heap of cold ash, striking a match that will not catch.",
    "「火还在底下烧，只是没人替它引路。」":
        "\"The fire still burns underneath — it just has no one to lead the way.\"",
    "「你要进去也行——带上这根火柴。里头的东西，只有烧穿了才肯让人过去。」":
        "\"You may go in — take this match. What lies within only lets you pass once it is burned through.\"",
    "「跟我走进火光里。」": "\"Come walk into the firelight with me.\"",
    "「不了，我再看看。」": "\"No. Let me look a while longer.\"",
    # 入口门：潮汐之门
    "潮汐之门": "The Tide Gate",
    "一扇向下的门，门缝里渗出退潮的水声与咸味。":
        "A door leading down; the sound of ebbing water and a salt tang seep through its seam.",
    "潮水的味道从门缝里渗出来。要走进去吗？":
        "The smell of the tide seeps from the door's seam. Step inside?",
    "走进去": "Step inside",
    "地图上出现了一扇「{name}」。": "A \"{name}\" appears on the map.",
    # 物品
    "引火人的火柴": "The Lighter's Match",
    "擦一下，你近旁的可燃物就烧起来。火焰会顺着燃料一路爬下去，浓气被引到就炸开。":
        "One strike and the flammables beside you catch. The flame crawls along the fuel, and thick gas detonates when reached.",
    "空白支票簿": "Blank Cheque Book",
    "一本从没写过数字的支票簿：想象力低到 25 点以下时，每回合多回流 1 点。":
        "A cheque book that never held a figure: below 25 imagination, each turn reflows 1 extra point.",
    "褪色的证件": "Faded ID Card",
    "证件上的字迹淡得认不出是谁：想象力低到 15 点以下时，每回合多回流 1 点。":
        "The writing is too faint to tell who it was: below 15 imagination, each turn reflows 1 extra point.",
    "回形针": "Paper Clip",
    "把两页空稿别在一起的那枚针：想象力低到 8 点以下时，每回合多回流 2 点。":
        "The clip that pinned two blank pages together: below 8 imagination, each turn reflows 2 extra points.",
    # 作用标签/说明
    "留白续写": "Blank-Edge Reflow",
    "引火": "Ignition",
    "想象力的自然回复若从「效力二」及以下起算，额外多回「效力」点。数量越多门槛越高（取最高的一条），越接近空槽收益越集中。":
        "When a natural imagination reflow starts at secondary power or lower, it restores extra points equal to power. More copies raise the threshold (highest wins); the nearer the tank is to empty, the more concentrated the gain.",
    "使用后点燃身边八格内所有可燃液体与气体（不入掉落池，随余烬廊桥进出授予与收回）。":
        "Use to ignite every flammable liquid and gas in the eight surrounding tiles (never in loot pools; granted on entering Ember Bridge and reclaimed on leaving).",
    # 余烬廊桥：终点三选一
    "余烬尽头的石台": "The Stone Table at the Ember's End",
    "石台上摆着几件被火烤过的旧物，等你挑一件带走。":
        "Fire-scorched relics lie on the stone table; pick one to take.",
    "火在身后熄了。石台上剩三件东西，都是烧不化的。":
        "The fire dies down behind you. Three things remain on the table, none of them burnable.",
    "取走纵火者怀表（点燃强度 +1）": "Take the Arsonist's Watch (ignition strength +1)",
    "取走爆破指环（爆炸半径 +1）": "Take the Blast Ring (explosion radius +1)",
    "取走凤凰羽衣（火焰免疫）": "Take the Phoenix Robe (fire immunity)",
    "取走余烬跟的靴子（点燃即撤步）": "Take the Ember-Heeled Boots (a free step when you ignite)",
    "「再看一眼，不取。」": "\"One last look — I'll take nothing.\"",
    # 退潮厅：出口与收缩
    "退潮的出口": "The Ebb's Exit",
    "潮水退到最后一圈，中心岛上一道门开着——跨出去，就能离开这里。":
        "The tide has ebbed to its last ring; a door stands open on the central island — step across and you leave this place.",
    "潮声从四面八方合拢。门就在岛上，跨出去。":
        "The sound of the tide closes in from every side. The door is on the island — step across.",
    "跨出去": "Step across",
    "再等等": "Wait a while longer",
    "身后的门合拢，退潮开始了。": "The door folds shut behind you; the ebb begins.",
    "潮水又漫过一圈——外环沉入意识边界。（第 {n} 环）":
        "The tide sweeps another ring — the outer ring sinks into the boundary of consciousness. (Ring {n})",
    "潮水已经漫过门槛，回头没有路了。": "The tide has crested the threshold; there is no way back.",
    # 进入/退出位面的消息
    "意识行囊已满，入口信物暂时没能带进来。":
        "Your mind-pack is full; the entry token could not be brought in.",
    "你手里多了「{item}」。": "You gained \"{item}\".",
    "一个守着火柴的人在梦层深处等你。":
        "Someone guarding a match waits for you deep in the dream layer.",
    "{name}的潮水漫过了你的脚踝——你被冲了出来，心智 −{n}。":
        "{name}'s tide washes over your ankles — you are flushed out, mind −{n}.",
    "这扇门已经关上了——本局不会再为你打开。":
        "This door is closed — it will not open for you again this run.",
    "近旁没有能引火的东西——先把燃料铺到身边。":
        "Nothing nearby can catch fire — lay some fuel down beside you first.",
    "火柴擦亮了——近旁的可燃物烧了起来。":
        "The match flares — the flammables beside you catch fire.",
}
