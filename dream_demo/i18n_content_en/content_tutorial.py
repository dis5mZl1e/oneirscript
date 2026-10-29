"""英文语言包 · 内容分册（由 scripts/_split_i18n_content.py 生成）。

教程/结算/FX/回忆/容器/投掷/远程武器/异象与物品描述/构想/弹体/事件/洞察/层主题/墙体/液体/气体/植物/征兆/图鉴——EN_CONTENT 主表及其全部增量 update。
键仍是中文原文；合并进 EN 的顺序见 dream_demo/i18n.py 末尾。
"""

from __future__ import annotations



EN_CONTENT: dict[str, str] = {
    "纸柄拆信刀": "Paper-handled Letterknife",
    "纸柄裂缝里露出旧信笺。刀尖停在封口，像是在等里面的人醒来。": "Old stationery shows through the split paper handle. The tip rests at the seal, as if waiting for whoever is inside to wake.",
    "近战创伤增量 1，基础出手耗时 1.1；占四格。“的”借出刀锋，“地”借出节拍，使关联攻击耗时减少 0.1，不额外借出刀锋。": "Melee trauma contribution 1; base attack time 1.1. Occupies four cells. Attribution lends its edge; manner lends its rhythm, reducing the bound attack's time by 0.1 without adding its edge damage.",
    "磨薄的袖套": "Threadbare Sleeve",
    "一只磨得透光的袖套。抬手时，布口比手腕先动半拍。": "A sleeve worn thin enough to let light through. When you raise your hand, its cuff moves half a beat ahead of your wrist.",
    "占四格；持续穿着时，攻击耗时减少 0.1。“的”或“地”关联攻击时，只借出本句节拍；同一件的持续效果不重复计算。": "Occupies four cells. Wearing it continuously reduces attack time by 0.1. Attribution or manner lends rhythm to the bound attack only; the same item's continuous effect is never counted twice.",
    "断齿顶针": "Broken-tooth Thimble",
    "顶针缺了一齿，凹槽里卡着蓝线。戴上后，指尖总想把断处拢到一起。": "The thimble is missing a tooth, with blue thread caught in its groove. Wear it, and your fingertip keeps wanting to draw broken edges together.",
    "占两格；持续佩戴时修缮量增加 20。“地”关联修缮时，只增加本次修缮量，仍需消耗实际修缮工具，不增加墙体完整度上限。": "Occupies two cells. Wearing it continuously adds 20 to repairs. Manner adds it only to the bound repair, which still consumes a real repair tool and cannot exceed the wall's integrity limit.",
    "留火的蜡笔": "Ember Crayon",
    "纸套烫得发软，蜡芯却没有燃烧。写到句末，纸边才冒出一点焦味。": "The paper wrapper softens with heat, though the wax has not caught fire. Only at the end of the sentence does the page smell faintly scorched.",
    "占五格；持续使用时点燃强度增加 1。“地”关联发射时，命中后尝试点燃已有燃料，成功另付 1 点想象力，点燃反馈冷却 6 回合。": "Occupies five cells. Continuous use adds 1 to ignition strength. Manner lets a bound shot try to ignite existing fuel on impact; success costs an extra 1 imagination and starts a six-round ignition feedback cooldown.",
    "复写刻刀": "Carbon-copy knife",
    "沿旧刻痕再划一遍：近战创伤 +3，基础攻击耗时 1.1。稳妥而略显迟缓。":
        "Trace the old groove again: melee trauma +3, base attack time 1.1. Reliable, but a little slow.",
    "近战创伤 +1；命中两成概率让对方直接睡去。":
        "Melee trauma +1; each hit has a 20% chance to put the target to sleep.",
    "跟着节拍出手：近战创伤 +2，攻击基础耗时 −0.3。":
        "Strike to the beat: melee trauma +2, base attack time -0.3.",
    "近战创伤 +2；命中两成概率删去对方最近获得的一条征兆。":
        "Melee trauma +2; each hit has a 20% chance to erase the target's newest portent.",
    "指尖涂着防滑的石墨粉。近战创伤 +1，攻击基础耗时 −0.2。":
        "Graphite grips your fingertips. Melee trauma +1, base attack time -0.2.",
    "清水向低处流；接触洗去可燃与酸蚀征兆，并扑灭身上的燃烧。":
        "Water flows downhill, washes away volatile and corroded portents, and puts out burning on your body.",
    "受压发电的地板：站上去每回合蓄 1 层电，离开每回合泄 1 层；攒满 4 层会放电（创伤 2，稳定意识不受伤，放电后退为普通地面），给周围 3×3 的意识体（包括自己）造成少量清醒创伤。":
        "Pressure builds one charge per round, fading by one after leaving. At four charges, a 3x3 arc deals 2 trauma, including to you, and consumes the floor. Stable minds are unharmed.",
    # ---- 0 层「梦的起始」教程与结算（2026-09-19） ----
    "梦的起始": "Origin of Dreams",
    "玩偶意识体": "Doll Echo",
    "迈出第一步": "First Steps",
    "意识面板": "The Mind Panels",
    "触碰即交锋": "Contact Is Combat",
    "让梦带你走": "Let the Dream Carry You",
    "下潜": "Dive",
    "任意键": "Any key",
    "方向键 / 小键盘": "Arrow keys / Numpad",
    "X": "X",
    "Tab": "Tab",
    "方向键（撞向目标）": "Arrow key (walk into it)",
    "F → 方向键": "F, then an arrow key",
    "X → O → Enter": "X, then O, then Enter",
    "N": "N",
    "随便按一个键": "Press any key",
    "走到 ◇": "Reach the ◇",
    "用 ? 对准 ◎": "Point the ? at the ◎",
    "打开行囊": "Open the inventory",
    "命中一次玩偶意识体": "Strike a Doll Echo",
    "发射并命中": "Fire and land a hit",
    "自动走到 ◈": "Auto-walk to the ◈",
    "按 N 下潜": "Press N to dive",
    "这里是所有梦开始的地方。": "This is where every dream begins.",
    "左侧是梦境本身；右侧是意识面板——心智、清醒度与想象力，事件记录与六个页签都在那边。":
        "The dream itself is on the left; the mind panels are on the right — mind, lucidity and imagination, plus the event log and six workspaces.",
    "用方向键或小键盘移动。WASD 被派给了面板选位，不负责走路。":
        "Move with the arrow keys or the numpad. WASD belongs to panel selection, not walking.",
    "走到亮起的 ◇ 上。每走一步，世界便流过一回合。": "Walk onto the lit ◇. Every step lets one turn flow past.",
    "按 X 进入观察模式，时间会为你停住。": "Press X to observe — time holds still for you.",
    "用方向键把 ? 移到亮起的 ◎ 上，读一读那株草——按 ' 可以展开它的详情。":
        "Move the ? with the arrow keys onto the lit ◎ and read the grass — press ' to unfold its details.",
    "按 Tab 打开行囊。行囊、携带意象（T）、征兆（V）、洞察（I）、观测（K）、操作（?）都列在右侧。":
        "Press Tab to open the inventory. Inventory, images (T), portents (V), insights (I), survey (K), actions (?) all live on the right.",
    "面板下方那行小字，是随时可查的键位备忘。":
        "The small line beneath the panel is a key reference you can check anytime.",
    "梦里的异象需要被解决。朝旁边发亮的玩偶意识体走过去——撞上它就是一次攻击。":
        "Anomalies in the dream must be resolved. Walk into the lit Doll Echo — walking into it is an attack.",
    "它不设防，也不记仇；散开之后，过一会儿会自己重新叠好。":
        "It is defenseless and holds no grudge; once scattered, it will fold itself back together before long.",
    "你带着 3 枚聚合弹。按 F 举起投射物，再按一个方向键把它射出去。":
        "You carry 3 aggregate rounds. Press F to raise a projectile, then an arrow key to let it fly.",
    "站到亮起的 ◆ 处，把远处那只玩偶打下来；瞄准时按 O 可以自动锁定最近的目标。":
        "Stand at the lit ◆ and shoot down the doll in the distance; while aiming, O locks onto the nearest target.",
    "按 X 观察、再按 O 开启辅助：一条淡黄的路径会铺到 ◎ 与你之间，按 Enter 沿它走过去。":
        "Press X to observe, then O for assist: a pale path is laid between you and the ◎; press Enter to walk it.",
    "直接用鼠标点远处同样可以——抵达 ◈ 时若踩着东西，顺手就会捡起。":
        "Clicking a distant tile with the mouse works too — arrive at the ◈ and anything there is picked up for you.",
    "联想盘：先放一件": "The Board: Place One",
    "新存档跳过教程": "Skip tutorial for new saves",
    "开启后新建存档直接进入第一层；不改变已有存档的教程状态。": "New saves begin in the first stratum. Existing saves keep their tutorial state.",
    "给句子加条件": "Give the Sentence a Condition",
    "T → Enter 拿起 → a → Enter": "T, Enter to lift, a to place, Enter to confirm",
    "拿起 → R → a → Enter": "Pick up, R, a to place, Enter to confirm",
    "写下带湿润条件、可以放电的句子": "Write a valid shock sentence with a wet condition",
    "把盐渍线圈摆到盘面第 1 列（条件位），水枪摆到同一行的第 5 列（行为位），按 Enter 确认整理。":
        "Put the Salt-Soaked Coil in column 1 (the condition slot) and the Water Gun in column 5 of the same row (the verb slot), then press Enter to confirm.",
    "条件只约束同一行：线圈给出「事件格导电才放行」，行为命中湿润位置时才出手。按 V 读整句。":
        "A condition binds its own row only: the coil grants 'fire only on a conductive cell', so the verb strikes when it lands on a wet cell. Press V to read the sentence.",
    "选装备 → Enter 拿起 → a 放下 → Enter 确认整理": "Pick an item, Enter to lift, a to place, Enter to confirm",
    "摆出条件位与行为位同行的成句盘面": "Form a sentence with condition and verb on one row",
    "教学行囊备有补丁睡衣和盐渍线圈。按 T 打开携带意象，选中一件按 Enter 拿进手里。": "Your tutorial pack has Patched Pajamas and a Salt-Soaked Coil. Press T for carried images, then Enter to lift one into your hand.",
    "方向键移动，a 放到盘上，再按 Enter 确认整理；确认后才生效。盘面逐行读词，不需要接线。": "Move with arrows, place with a, then confirm with Enter. Changes take effect on confirmation. Words are read row by row; no wires are needed.",
    "在编辑器拿起一件按 R 旋转，用方向键挪位、a 放下，再放第二件并按 Enter 确认整理。旋转只改变形状。": "Pick up an image, rotate with R, move with arrows and place with a. Add a second image and confirm with Enter. Rotation only changes its shape.",
    "转一转，腾出空间": "Turn It, Make Room",
    "Tab → 选中 → U → Enter": "Tab, select, U, then Enter",
    "选中 → R → 方向键": "Select, R, then an arrow key",
    "插片 → 线 → Enter": "Piece, wire, then Enter",
    "让盘上多留下一件装备": "Leave one more image on the board",
    "旋转之后盘上至少有两件": "Have at least two images placed after rotating",
    "让一条线路穿过湿润门": "Run a live line through a Wet Gate",
    "行囊里选中一件携带意象，按 U 进入联想盘编辑器，摆好再按 Enter 确认。":
        "Select a carried image in the inventory, press U to open the association board editor, place it, then press Enter to commit.",
    "很多意象不接线也照常生效——盘上的面积就是它的身体。":
        "Many images work without any wiring at all — the area they hold on the board is their body.",
    "盘面只有 8×6 格，放不下时先别丢。":
        "The board is only 8×6 cells. Before you drop something, try fitting it.",
    "选中盘上的件按 R 旋转、再用方向键挪一格：转个方向往往就挤出下一件的位置。":
        "Select a piece on the board, press R to rotate and move it with the arrow keys: one turn often opens room for the next.",
    "右侧取一枚「湿润门」串进线路，再接上一枚会做事的反馈插片，确认。":
        "Take a Wet Gate from the right-hand palette, thread it into a line, then attach a feedback piece that actually does something and commit.",
    "闸门只放行落点上真有导电液体的事件——被水浇过的地方才算数。":
        "The gate only lets through events whose destination truly holds conductive liquid — only ground soaked with water counts.",
    "在更深的梦层，崩解度满 100 才允许下潜；这里不需要。":
        "In deeper strata, dissolution must reach 100 before you may dive; here it does not.",
    "亮起的 ▼ 只是提醒：随时按 N，离开梦的起始。下潜之后，这里不再为你重开。":
        "The lit ▼ is only a reminder: press N anytime to leave the Origin of Dreams. Once you dive, it will not reopen for you.",
    "引导完成——梦层在等你按 N 下潜。": "Tutorial complete — the dream strata await. Press N to dive.",
    "引导结束。梦层在等你按 N 下潜。": "Tutorial dismissed. The dream strata await. Press N to dive.",
    "已跳过：{title}。": "Skipped: {title}.",
    "梦的起始在你身后合拢。": "The Origin of Dreams closes behind you.",
    "✦ {current}/{total} · {title}": "✦ {current}/{total} · {title}",
    "▸ {key} — {goal}": "▸ {key} — {goal}",
    "Delete 跳过此步 · Esc 返回/暂停 · n 随时下潜离开": "Delete skips this step · Esc returns/pauses · n dives out anytime",
    "你离开了梦的起始——它在你身后合拢。": "You left the Origin of Dreams — it closed behind you.",
    "起点已经合拢，回不去了。": "The origin has closed. There is no going back.",
    "散开的纸屑慢慢浮起——玩偶意识体重新叠好了自己。":
        "The scattered paper drifts upward again — the Doll Echo has folded itself back together.",
    "你在梦的起始醒来。跟随左侧的引导，或随时按 N 下潜。":
        "You wake in the Origin of Dreams. Follow the guide on the left, or press N anytime to dive.",
    "玩偶意识体散成一地纸屑——它过一会儿会重新叠好自己。":
        "The Doll Echo scatters into a drift of paper — it will refold itself in a while.",
    "深潜回合": "Turns dreamed",
    "抵达最深层": "Deepest stratum",
    "击破异象": "Anomalies resolved",
    "复合事件": "Compound events",
    "引燃次数": "Ignitions",
    "物品使用": "Items used",
    "承受创伤": "Trauma taken",
    "自我线索": "Threads of self",
    "{count} 段记忆沉入长夜：{names}{more}": "{count} memories sink into the long night: {names}{more}",
    "这一局没有带走任何记忆碎片。": "This run carries no memory fragments away.",
    "……": "…",
    # ---- FX 特效层（2026-09-19） ----
    "画面特效已开启——设置页「画面特效」可调整或关闭。":
        "Visual effects are on — adjust or disable them via \"Visual effects\" in Settings.",
    "无梦": "Dreamless",
    "裂隙尽头是清晨": "Morning waits past the rift",
    "这是我的故事，包括写坏的部分": "This is my story, spoiled pages included",
    "故事由它收尾，你如释重负": "It finished the story for you, and you feel lighter",
    "两支笔同时落下": "Two pens set down at once",
    "梦不再需要你": "The dream no longer needs you",
    "意识与清醒一同耗尽": "Mind and lucidity spent together",
    # ---- 0 层教学向导（npc.origin_greeter）与对话步 ----
    "迎面的纸偶": "Greeter Papercraft",
    "叠得不太整齐的纸偶，站在所有梦的入口处，专门负责打招呼。":
        "A papercraft figure folded none too neatly, standing at the entrance to every dream, greeting newcomers.",
    "纸偶朝你歪了歪头：「欢迎。这里是所有梦开始的地方——别的我先不说，赶路要紧。」":
        "The paper figure tilts its head: \"Welcome. This is where every dream begins — the rest can wait; the road matters.\"",
    "「这里是什么地方？」": "\"What is this place?\"",
    "「你为什么在这里？」": "\"Why are you here?\"",
    "「告辞。」": "\"Farewell.\"",
    "「梦的起始。往后的每一层都比这里深，也比这里吵。」":
        "\"The Origin of Dreams. Every stratum past this one runs deeper — and louder.\"",
    "「总得有人站在门口，跟每一场新梦问声好。我叠得不够整齐，但胜在勤快。」":
        "\"Someone has to stand at the door and greet each new dream. I'm folded crooked, but I'm diligent.\"",
    "打招呼": "Say Hello",
    "E / 左键": "E / left click",
    "与纸偶说上一次话": "Speak with the paper figure",
    "梦里不止你和异象。走到迎面的纸偶身边，按 E（或左键点它）开口——有的意识愿意交谈，有的只顾着追你。":
        "You are not alone in the dream. Walk up to the Greeter Papercraft and press E (or left-click it) — some minds will talk; the rest only chase.",
    "它只陪聊天，不做买卖；聊完按 Esc 收起对话。":
        "It only chats — no trades. Press Esc to close the conversation.",
    "{name}：{reply}": "{name}: {reply}",


    # ---- 旧梦回忆（主页游玩历史页） ----
    "回忆": "Memories",
    "还没有任何一场结束的梦。": "No dream has yet run its course.",
    "通关": "Won",
    "陨落": "Lost",
    "梦层 {d}": "Stratum {d}",
    "—— 本局 ——": "— This Run —",
    "—— 携带意识 ——": "— Carried Images —",
    "空空如也。": "Nothing at all.",
    "（{slot}）": "({slot})",
    "—— 洞察 ——": "— Insights —",
    "—— 构想 ——": "— Abilities —",
    "—— 记忆碎片 ——": "— Memory Fragments —",
    "游玩 {runs} 次 · 通关 {wins} 次": "{runs} runs · {wins} won",
    "↑↓/滚轮 选择 · Enter/左键 查看详情 · Esc/Q 返回": "↑↓/wheel to choose · Enter/left click for details · Esc/Q back",
    "滚轮/↑↓ 滚动 · Esc/Q/Enter 返回列表": "wheel/↑↓ to scroll · Esc/Q/Enter back to list",
    "你选择了清晨，把梦留在稿纸背面。": "You chose the morning and left the dream on the back of the page.",
    "你夺回了笔，连同写坏的部分一起。": "You took back the pen — spoiled pages included.",
    "故事由它收尾，你空着一块地方醒来。": "It finished the story for you; you woke with a hollow somewhere.",
    "两支笔同时落下，谁也没盖过谁。": "Two pens set down at once, neither overwriting the other.",
    "啼哭止息，你在最深处找到了醒来的条件。": "The cry fell silent; at the deepest point you found the conditions of waking.",
    "意识沉没于深层边界": "Consciousness sank into the deep boundary",
    "意识被『{name}』摧毁了": "Consciousness was torn apart by ‘{name}’",
    "你因为『{name}』失去了意识": "You lost consciousness to ‘{name}’",



    # ---- 容器浮层与获取渠道（2026-09-19） ----
    "1/左键 盛装 · 2/左键 倒出 · Esc 收起（留在行囊）": "1/left click fill · 2/left click pour · Esc puts it away (stay in inventory)",
    "拾荒者的提箱": "The Scavenger's Case",
    "桥洞下摆着一只上了锁的提箱，锁孔却被撬成了大开口——主人显然不打算再回来。":
        "Under the bridge sits a locked case with its keyhole pried wide open — its owner clearly isn't coming back.",
    "提箱里码着几件器物：耐热的瓶、隔层的管、绷紧的气球，还有一台说不清原理的容器。":
        "The case holds several vessels: a heatproof bottle, a partitioned tube, a taut balloon, and one container of unclear principle.",
    "旁边的纸条写着：「拿点梦的原料来换。瓶子只认液体，气球只认气。」":
        "A note beside it reads: \"Trade some raw dream for them. Bottles take only liquid; balloons only gas.\"",
    "想象力 −4，换一只玻璃瓶（单种液体 · 少见）": "Imagination −4 for a glass bottle (one liquid · uncommon)",
    "清醒 −3，换一只气球（单种气体 · 少见）": "Lucidity −3 for a balloon (one gas · uncommon)",
    "想象力 −8，换一支理想试管（多种液体 · 非常稀有）": "Imagination −8 for an ideal tube (many liquids · very rare)",
    "心智 −8，换一台理想气体容器（多种气体 · 非常稀有）": "Mind −8 for an ideal vessel (many gases · very rare)",
    "轻轻带上箱盖": "Close the lid gently",
    "交出消耗品，换一只玻璃瓶（单种液体）": "Hand over consumables for a glass bottle (one liquid)",
    "交出消耗品，换一只气球（单种气体）": "Hand over consumables for a balloon (one gas)",
    "交出消耗品，换一支理想试管（多种液体）": "Hand over consumables for an ideal tube (many liquids)",
    "付清醒度，换一台理想气体容器（多种气体）": "Pay lucidity for an ideal vessel (many gases)",



    # ---- 投掷系统（core/throwing.py，2026-09-19） ----
    "举起{item}——点选落点或按方向键投掷（Esc 取消，不消耗）。":
        "Raise {item} — pick a landing spot or press an arrow key (Esc cancels; nothing is consumed).",
    "太远了，扔不到（最远 {n} 格）。": "Too far to throw (max {n} tiles).",
    "那里没有落脚点。": "There is no footing there.",
    "投掷。": "Threw it.",
    "冰面太滑，停不在那个格子上。": "The ice is too slippery — you can't stop on that tile.",
    "把{item}压入膛——点选方向或按方向键发射（Esc 取消，不消耗）。":
        "Load {item} — pick a direction or press an arrow key to fire (Esc cancels; nothing is consumed).",
    "不能扔进坚实聚合物里。": "You cannot throw it into solid polymer.",
    "看不见那里，落点无从确认。": "You cannot see that spot, so the landing can't be confirmed.",
    "交出消耗品，换一支燃烧瓶（投掷引火）": "Hand over consumables for a molotov (thrown fire)",
    "交出消耗品，换一枚雷管胶囊（投掷爆破）": "Hand over consumables for a detonator capsule (thrown blast)",
    "想象力 −5，换一支燃烧瓶（投掷引火）": "Imagination −5 for a molotov (thrown fire)",
    "心智 −6，换一枚雷管胶囊（投掷爆破）": "Mind −6 for a detonator capsule (thrown blast)",



    # ---- 远程武器批次（喷水枪/吹风机/钉枪/音爆哨/冻凝镖枪/投石索/投掷物/光焰弹） ----
    "喷水枪": "Water Gun",
    "吹风机": "Hair Dryer",
    "钉枪": "Nail Gun",
    "音爆哨": "Sonic Whistle",
    "冻凝镖枪": "Frost Dart Gun",
    "投石索": "Sling",
    "蜂鸣诱饵": "Buzz Lure",
    "烟雾罐": "Smoke Canister",
    "光焰弹": "Flare Bolt",
    "一只耐热的空瓶，瓶口还留着上一位使用者的指纹。盛一种液态记忆，至多二十五点，倒在任何你想倒的地方。": "A heatproof bottle bearing the last user's fingerprints. Holds one liquid memory, up to twenty-five; pour it wherever you like.",
    "管腔彼此隔开，像几段互不打听的心事。多种液态记忆可同时盛放而互不沾染，合计二十五点，倒出时先后由你。": "Partitioned chambers like secrets that never ask after each other. Holds several liquid memories at once, twenty-five total; you choose the pouring order.",
    "气球绷得紧紧的，里面关着一口抓来的弥散印象——至多二十五点。解开扎口，它就回到你想让它去的地方。":
        "The balloon is stretched taut around a captured diffuse impression — up to twenty-five. Untie the knot and it returns wherever you send it.",
    "内胆一层隔一层，各装各的气，谁也不碰谁。合计二十五点，放气时一次一种，次序由你。":
        "Layer within layer, each holding its own gas, touching no one. Twenty-five total; release one kind at a time, in your order.",
    "枪管里晃着半管来路不明的水。发射液态记忆：淋在墙上淌成滩，浇在意识体上留一层。有装液体的容器就抽容器，没有就只能喷少量清水；每次发射耗费一点想象力。":
        "Half a tube of untraceable water sloshes in the barrel. Fires liquid memory: splashing into pools on walls, leaving a film on consciousnesses. Draws from liquid containers when possible; otherwise sprays a little clean water. Each shot costs a little imagination.",
    "热风档早坏了，冷风档吹出来的都是别人的梦。发射弥散印象：喷在墙上凝成雾，罩在意识体上散成一层。有装气的容器就抽容器，没有就只能吹少量水蒸气；每次发射耗费一点想象力。":
        "The hot setting broke long ago; the cool wind carries other people's dreams. Fires diffuse impressions: misting onto walls, settling over consciousnesses. Draws from gas containers when possible; otherwise puffs a little vapor. Each shot costs a little imagination.",
    "木工房里顺出来的大家伙。钉一发要顶两个回合的力，但钉进去了就拔不出来——穿透力极强，创伤沉重。":
        "A heavyweight smuggled out of a woodshop. Each nail takes two turns of effort, but once it's in, it stays — exceptional penetration, heavy trauma.",
    "吹不响的哨子改装的。半回合一声爆鸣，几乎造不成创伤，却能把命中处的对象掀出去，声响还会引来半层梦的注意。":
        "A whistle remade into a bang. Half a turn per blast; it barely wounds, but knocks the target flying and drags half a stratum's attention to the impact.",
    "镖尖凝着一种醒不过来的凉意。命中即冻：被射中的异象会慢慢结上一层霜，动作与出手都迟滞下来。":
        "The dart tips carry a chill you can't wake from. On hit, frost: the struck anomaly slows its movements and attacks.",
    "皮兜磨得发亮。挎上它，你扔什么都又远又稳：投掷距离 +3，投掷物的爆破与引火威力 +1。":
        "A leather pouch worn smooth. Sling it on and everything you throw flies farther and truer: throw range +3, thrown blast and fire power +1.",
    "捏一下就嗡嗡作响的铁皮虫。扔出去落地即响，第 3、6 回合各再响一次：半径内的异象都会循声扑向响处——包括你想支开的那只。":
        "A tin bug that buzzes when squeezed. It sounds off on landing and again on rounds 3 and 6: every anomaly in range rushes toward the noise — including the one you wanted away.",
    "拉环一拔就滚滚冒烟的罐头。扔到哪儿，哪儿就糊上一团浓黑的弥散印象——看不清的地方，梦也认不出你。":
        "Pull the ring and it pours smoke. Where it lands, a thick black impression blurs the dream — where nothing is clear, the dream can't pick you out.",
    "装填后沿直线飞出：撞上第一个障碍或意识体便尝试点燃该格可燃材料，烧成一小片光。缺燃料时只闪一下，不承诺持续火场。":
        "Load it and it flies a straight line: on the first obstacle or consciousness it meets it tries to catch that tile's flammable material alight, burning into a patch of light. Without fuel it only flashes and promises no lasting fire.",
    "喷射弹药": "Spray Ammo",
    "↑↓ 选择 · Enter/左键 选用 · Esc 取消": "↑↓ choose · Enter/left click to load · Esc cancels",
    "液态记忆泼在……": "",
    "水线还没成形就散了。": "The spray dissipated before it formed.",
    "{medium}泼在 {entity} 身上，留下薄薄一层。": "{medium} splashes over {entity}, leaving a thin film.",
    "{medium}泼在梦的表面（{kind} {amount}）。": "{medium} splashes across the dream's surface ({kind} {amount}).",
    "光焰弹没有落点。": "The flare bolt found no landing.",
    "光焰弹在 {entity} 身上烧成一小片光。": "The flare bolt burns into a patch of light on {entity}.",
    "光焰弹炸开，火焰照亮了一小片梦。": "The flare bolt bursts, lighting a small patch of the dream.",
    "光焰弹烧尽了，什么也没有点着。": "The flare bolt burns out without catching anything.",
    "{name}没有落点。": "The {name} found no landing.",
    "电弧弹在 {entity} 身上跳成一道短路，这里没有可传播的导电介质。":
        "The arc bolt shorts out across {entity}; nothing here carries the current.",
    "电弧弹打在绝缘的表面上，电弧只闪了一下就散了。":
        "The arc bolt strikes an insulating surface; the arc flickers and dies.",
    "电弧弹在 {entity} 身上接通 {count} 格导电介质，电场留在原地等谁踩。":
        "The arc bolt closes {count} tiles of conductive medium across {entity}, leaving the field waiting for a footstep.",
    "电弧弹落在导电介质上，接通 {count} 格电场。":
        "The arc bolt lands in conductive medium, charging {count} tiles of electric field.",
    "{name}在火里烧尽了。": "{name} burns away in the fire.",
    "想象力不足（喷射需要 2 点）。": "Not enough imagination (spraying costs 2).",
    "想象力不足（喷射需要 {cost} 点）。": "Not enough imagination (spraying costs {cost}).",
    "喷射方向无效。": "Invalid spray direction.",
    "喷射。": "Sprayed.",
    "喷射弹药": "Spray Ammo",
    "环境反应": "Reactions",
    "液枪：喷射液态记忆": "Liquid gun: sprays liquid memory",
    "拍立得墙": "Polaroid Wall",
    "整面墙贴满晃动的拍立得，全都拍的是你的背影。": "A wall papered with trembling polaroids, every one a photograph of your back.",
    "生锈的水龙头": "The Rusted Faucet",
    "水龙头拧不开，却在往外渗水——滴答声精确得像节拍器。": "The faucet won't turn, yet it weeps water — dripping with the precision of a metronome.",
    "走字的电表": "The Racing Meter",
    "一只电表在没人用电的房间里疯转，数字跳得像心跳。": "A meter spins wildly in a room using no power, digits leaping like a heartbeat.",
    "纸月亮": "Paper Moon",
    "窗外挂着一轮有折痕的月亮，光落在地上沙沙作响。": "A creased moon hangs at the window; its light rustles as it lands.",
    "无主的行李": "Unclaimed Luggage",
    "行李箱在走廊尽头转圈，像在等一个不会来认领它的人。": "A suitcase circles at the corridor's end, waiting for an owner who isn't coming.",
    "雾中之琴": "Organ in the Fog",
    "浓雾里有一架管风琴在自我演奏，音栓上刻着各种天气。": "In the fog a pipe organ plays itself, its stops carved with kinds of weather.",
    "抽屉之夜": "Night of the Drawer",
    "床头柜的抽屉半开着，里面传出翻纸的声音。": "The nightstand drawer sits half-open; paper rustles inside.",
    "寄往醒处的邮筒": "Mailbox to Waking",
    "一只邮筒立在梦的裂缝旁，投递口朝着「醒」的方向。": "A mailbox stands by the dream's rift, its slot aimed toward waking.",
    "工具箱之墓": "Grave of the Toolbox",
    "一只工具箱被郑重地埋在土里，墓碑是一把扳手。": "A toolbox is solemnly buried in the dirt, its headstone a wrench.",
    "潮汐钟": "The Tide Clock",
    "一只挂钟的指针以潮水的节奏倒着走。": "A wall clock whose hands run backward to the rhythm of tides.",
    "守塔人的夜班表": "The Keeper's Night Watch",
    "记得某人替整片海守过夜。": "Remembers someone who kept the night watch for the whole sea.",
    "结霜的信封": "The Frosted Envelope",
    "记得一封没敢拆的信在窗台上过了整个冬天。": "Remembers an unopened letter spending all winter on the sill.",
    "油漆味的走廊": "The Fresh-Paint Corridor",
    "记得一条刚刷过漆、亮得晃眼的走廊。": "Remembers a freshly painted corridor, bright enough to sting.",
    "共伞的雨声": "Rain Under a Shared Umbrella",
    "记得半边肩膀湿透的距离。": "Remembers the distance at which one shoulder gets soaked.",
    "灵感咖啡": "Inspiration Coffee",
    "苦到灵魂发抖的一小杯，喝完的瞬间脑子里多出三个没写过的开头。想象力 +16。": "A tiny cup bitter enough to shiver the soul; the instant you finish it, three unwritten openings appear. Imagination +16.",
    "安眠含片": "Sleep Lozenge",
    "含一片，梦替你把没做完的事做完一半。清醒度 +6。": "Let one dissolve and the dream finishes half of what you left undone. Lucidity +6.",
    "高压水泵": "High-Pressure Pump",
    "给喷水枪加装的第二级压水膛：每次喷射的材料量 +6。": "A second pressure chamber for the water gun: +6 material per spray.",
    "聚气喷嘴": "Air Concentrator Nozzle",
    "把散风收束成一道风柱：吹风机每次喷射的材料量 +6。": "Collar the scattered wind into a column: +6 material per dryer spray.",
    "投掷手套": "Throwing Gloves",
    "掌心缝着防滑胶粒的手套：投掷距离 +3，投掷威力 +1。": "Gloves stitched with gripping studs: throw range +3, thrown power +1.",
    "调焦环": "Focus Ring",
    "套在指间旋动的黄铜环，替你的眼睛校准弹道：弹体穿透 +1。": "A brass ring spinning between your fingers, calibrating your eye: projectile penetration +1.",
    "焦油燃烧弹": "Tar Firebomb",
    "掺了焦油的燃烧弹，火更黏、更久、更不讲道理：十字上会分三批淌出燃油，一批二十。":
        "A firebomb cut with tar — the flame is stickier, longer, less reasonable. The cross takes its fuel in three pours of twenty units each.",
    "烟雾双联罐": "Twin Smoke Cans",
    "两只烟雾罐用胶带缠成一枚：一次投掷只放一只，另一只留在手里，想放的时候再花一次行动。":
        "Two smoke cans taped into one: a throw releases only one; the other stays in your hand until you spend another action on it.",
    "聚合弹匣·大": "Aggregate Clip, Jumbo",
    "十枚聚合弹排得整整齐齐，像一排等着被念出的名字。聚合弹 +10。": "Ten aggregate rounds in a tidy row, like names waiting to be called. +10 rounds.",
    "电弧弹": "Arc Bolt",
    "一发裹着电弧的直线弹：沿路途烙过去，撞上导电介质就接通一片电场。":
        "A straight bolt sheathed in arc: it brands the road it flies, and on a conductive medium it closes a patch of electric field.",
    "洞察之镜": "Mirror of Insight",
    "核心执念崩解时凝成的小镜。照一照，镜中会浮现三种你可能成为的领悟——选一种留下，镜子随之碎裂。": "A small mirror condensed from a core obsession's remains. Look, and three insights you might become surface — keep one, and the mirror shatters.",
    "冻凝构想": "Frost Design",
    "想象一场悄无声息的霜：冻结近旁 3 格内所有失控意识 3 回合。": "Imagine a soundless frost: freeze every stray consciousness within 3 tiles for 3 turns.",
    "烟幕构想": "Smoke Veil Design",
    "在脚下唤出一团浓黑的弥散印象，遮蔽与匿名一步到位。": "Summon a billowing black impression at your feet — concealment and anonymity in one step.",
    "显影拓印": "Developing Print",
    "把想象力泼在黑暗上：以自身为中心，永久显影半径 8 内的地形。": "Splash imagination onto the dark: permanently develop terrain within radius 8 of you.",
    "夜视": "Night Eyes",
    "愈合梦": "Healing Dream",
    "蜂鸣回响": "Buzzing Echo",
    "镜面泛起涟漪——三种可能的领悟浮现出来。": "The mirror ripples — three insights you might become surface in the glass.",
    "镜面碎裂——你留下了「{insight}」。": "The mirror shatters — you keep “{insight}”.",
    "镜面里没有这个映像。": "That image is not in the glass.",
    "你没有洞察之镜。": "You carry no Mirror of Insight.",
    "霜沿着脚蔓开：冻结了 {n} 个近旁的失控意识（{turns} 回合）。": "Frost creeps from your feet: {n} nearby stray consciousnesses frozen ({turns} turns).",
    "浓黑的烟幕在你脚下铺开。": "A billowing black smoke spreads beneath you.",
    "想象力泼进黑暗：显影了 {n} 格地形。": "Imagination splashed onto the dark: {n} tiles of terrain developed.",
    "↑↓ 选择 · Enter/左键 选定（消耗镜） · Esc 收回": "↑↓ choose · Enter/left click to keep (consumes the mirror) · Esc to withdraw",
    "核心执念的残骸里凝出一面「洞察之镜」。": "A “Mirror of Insight” condenses from the core obsession's remains.",
    "拾荒者": "The Scavenger",
    "夜药剂师": "The Night Pharmacist",
    "档案员": "The Archivist",
    "引路人": "The Guide",
    "报童阿全": "Newsboy Quan",
    "拾荒协会登记员": "Scavenger Guild Registrar",
    "失物招领员": "Lost-and-Found Clerk",
    "织梦酒保": "Dreamweaver Bartender",
    "无名诗人": "The Nameless Poet",
    "记忆当铺老板": "The Memory Pawnbroker",
    "灯塔的光压碾过来——清醒度被抽走了一缕。": "The lighthouse's light-pressure grinds over you — a wisp of lucidity drawn away.",
    "灯塔的光里走出一小簇新的影子。": "A small new shadow steps out of the lighthouse's light.",
    "一个巨大的句号吞掉了你两笔想象力。": "A giant period swallows two points of your imagination.",
    "句子被迫停顿——你被句号冻在原地。": "The sentence is forced to pause — the period freezes you in place.",
    "未完成句号折出一只折页人，替它继续写。": "The unfinished period folds a paper figure to keep writing for it.",
    "一声啼哭震荡整层梦——心智 −2，所有异象都醒了。": "A cry shakes the whole stratum — mind −2, every anomaly wakes.",
    "冻嚎掠过——你的膝盖结满了霜。": "A freezing howl sweeps past — your knees crust over with frost.",
    "啼哭的回声里钻出一条思维蠕虫。": "Out of the cry's echo crawls a thought worm.",
    "执笔者删掉了你的一段独白——心智 −2。": "The Scribe deletes a passage of your monologue — mind −2.",
    "执笔者笔下多出一道影子，替它续写。": "Another shadow joins the Scribe's pen, writing on in its place.",
    "气枪：喷射弥散印象": "Gas gun: sprays diffuse impressions",
    "投掷强化：距离+3、威力+1": "Throw mastery: range +3, power +1",
    "落点声波引怪": "Lands with a luring sound pulse",
    "落点糊上黑烟": "Lands in a puff of black smoke",
    "一次性直线发射": "One-shot straight fire",
    "受击反打冲击": "Countershocks attackers",
    "命中删征兆": "Strikes may erase a portent",
    "命中删最近征兆": "Strikes may erase the newest portent",
    "命中附加深眠": "Strikes may cause deep sleep",
    "徒手操作机关": "Safe bare-handed mechanisms",
    "液体征兆减半": "Halves liquid portents",
    "隔墙听轮廓": "Hears outlines through walls",
    "喷射材料量 +6": "Spray material +6",
    "洞察三选一": "Pick one of three insights",
    "{target}被「{portent}」缠上了。": "{target} is wrapped in “{portent}”.",
    "{item}嗡嗡作响——半层梦的注意力都被它拽了过去。": "{item} buzzes loudly — half the stratum's attention drags toward it.",
    "罐头炸开，浓烟糊满了梦。": "The canister bursts, smearing the dream with thick smoke.",



    # ---- 异象描述（名称多在 i18n.EN 里） ----
    "由反复折叠的纸页聚成，会沿可辨认的边缘追逐声音；长时间停留后，远处的结构会重新生成它。":
        "Folded from page upon page, it chases sound along any edge it can make out; linger too long and distant structures will spawn it again.",
    "轮廓像一张被迫对折的人形说明书。": "Its outline is a human instruction sheet forced into a fold.",
    "先留下回声，随后才完成敲击。": "The echo arrives first; the strike finishes after.",
    "不断移动不存在的模型零件，拒绝承认房间已经改变。":
        "It keeps moving model parts that do not exist, refusing to admit the room has changed.",
    "它面向一处空白，等待并不存在的演出继续。":
        "It faces a blank space, waiting for a performance that isn't there to go on.",
    "表面温度持续下降，动作却比大多数意识更快。": "Surface temperature keeps dropping, yet it moves faster than most.",
    "表面温度持续下降，动作缓慢却从不迟到。": "Surface temperature keeps dropping — slow, but never late.",
    "从无法辨认的背光中阅读玩家留下的路径。":
        "It reads the paths you leave, backlit beyond recognition.",
    "一扇会自行游荡的门，把目击信息传到相邻结构。":
        "A door that wanders on its own, passing sightings to neighbouring structures.",
    "它删改周围对象的边界，却从不在批注里留下署名。":
        "It edits the boundaries of everything nearby, yet never signs its annotations.",
    "两个不相邻的房间在它的轮廓内占据同一位置。":
        "Two rooms that never touch occupy the same place inside its outline.",
    "所有未完成的句子都试图在这里获得同一个结尾。":
        "Every unfinished sentence tries to find the same ending here.",
    "钟摆每摆过一个整点，就把整层梦境敲醒一次。":
        "Each hour the pendulum passes, it wakes the whole layer once.",
    "你向左，它便向右；你们共享一条看不见的对称轴。":
        "You step left, it steps right; you share an invisible axis of symmetry.",
    "折痕是它的鳍，液面是它的天空；上岸时几乎无法移动。":
        "Creases are its fins, the liquid surface its sky; on dry land it can barely move.",
    "它仍在为不存在的客人改衣，剪刀顺手剪走口袋里的东西。":
        "It still alters clothes for guests who aren't there, and its shears clip whatever is in your pocket.",
    "静止时它与家具没有区别，直到你走进它的影子。":
        "At rest it is indistinguishable from furniture — until you step into its shadow.",
    "一段没有尽头的脚步声，沿着固定的楼梯上下巡逻。":
        "An endless footstep patrols a fixed staircase, up and down.",
    "同一张底片上站着两个它，哪一个都是真的。":
        "Two of it stand on the same negative, and both are real.",
    "湿透的乐谱让每一个声部都急着追上另一个。":
        "The soaked score makes every voice hurry to catch another.",
    "一段楼梯决定去它从未连接过的楼层，途中不绕开任何人。":
        "A staircase decides to visit a floor it never connected to, and avoids no one on the way.",
    "它照亮整片梦境，却照不进自己的空腔。":
        "It lights the whole dream, but never the hollow inside itself.",
    # ---- 物品描述 ----
    "把一句未说完的话压成直线弹体。携带后获得发射许可。":
        "Presses an unfinished sentence into a line projectile. Equipping it grants fire clearance.",
    "弹体会记住穿过第一层阻挡后的方向。":
        "The projectile remembers its heading after breaking the first layer of cover.",
    "掷到落点才炸：半径 2 内造成创伤并把目标推开一格，削薄坚实聚合物、引燃可燃材料；自己站在半径里照样挨一下清醒创伤。":
        "It bursts where it lands: trauma inside radius 2, targets shoved a cell aside, solid aggregate chewed thinner and flammable material caught alight — stand in that radius yourself and you take lucidity trauma too.",
    "点燃一格液态记忆或高浓度弥散印象。":
        "Ignites one cell of liquid memory or dense diffuse impression.",
    "把导电液态记忆里的电压借给相邻目标。":
        "Borrows voltage from conductive liquid memory and lends it to an adjacent target.",
    "苦味仍然可靠。恢复想象力 10。": "The bitterness still works. Restores 10 imagination.",
    "展开后只能维持一次发射。": "Once unfolded, sustains a single shot.",
    "让远处的声音先抵达你。": "Lets distant sounds reach you first.",
    "记得某种不会停机的雨。": "Remembers a rain that never stops.",
    "每次读错一个词，就多看见一条路。": "Every word misread reveals one more path.",
    "拧紧一个错误，也许会松开另一个。": "Tighten one mistake and you may loosen another.",
    "让一次追踪暂时忘记目的地。": "Makes a pursuit forget its destination for a while.",
    "恢复少量心智，但让下一次移动迟疑。":
        "Restores a little mind, but makes the next move hesitate.",
    "短暂固定远处的形状。": "Briefly pins the shape of something far away.",
    "按下它，三格内看得见的一个机关就替你先动一次。":
        "Press it and one mechanism you can see within three cells moves once, ahead of you.",
    "有人把天气录成了背景音。": "Someone recorded the weather as background noise.",
    "每一盏灯都照着尚未拼完的部分。": "Every lamp lights a part not yet assembled.",
    "副歌之后仍有一段空白。": "After the chorus there is still a blank.",
    "纸张最外侧也曾经是正文。": "The outermost edge of the page was once body text.",
    "齿轮没有带动机器，只带动了时间。": "The gear drove no machine, only time.",
    "把一件易逝物挂在梦的墙上，让打击先落在它身上。":
        "Hangs a perishable on the wall of the dream so blows land on it first.",
    "只有一边的声音，让你更难被声音找到；代价是听不见脚下的提示。":
        "Sound from one side only makes you harder to find by sound; the cost is not hearing prompts underfoot.",
    "指针停在某一回合，附近的梦因此走得慢一些。":
        "Its hands stop at a certain round, so nearby dreams walk slower.",
    "下潜后的最初几回合，它仍替你照亮远处。":
        "For the first few rounds after descending, it still lights the distance for you.",
    "把一段楼梯重新拧回原位，也能修好别的墙。":
        "Bolts a staircase back into place, and can mend other walls too.",
    "拉到悬停的格子，读出你们之间最短的谎言。":
        "Pull it to the hovered cell and read the shortest lie between you.",
    "墨迹晕开的地方，原本写着休止符。": "Where the ink bled, a rest note used to be.",
    "每一层灰都记得自己落下的年份。": "Every layer of dust remembers the year it fell.",
    "窗外的东西移动得比车快。": "Things outside the window move faster than the train.",
    "醒一半，梦一半。恢复清醒度 6 与想象力 4。":
        "Half awake, half dreaming. Restores 6 lucidity and 4 imagination.",
    "糖衣之下要么是救济，要么是账单。":
        "Under the sugar coat lies either relief or a bill.",
    "想象力立刻沸腾，清醒度随后分期偿还。":
        "Imagination boils at once; lucidity is repaid in instalments.",
    "冲开迟滞与麻痹攒下的欠账，顺便暖一点心智。":
        "Clears the debt banked up by sluggishness and numbness, warming the mind a little.",
    "提神醒脑：持续期间每 2 回合恢复 1 点清醒度（总量 14）。":
        "Sharpens the mind: while active, restores 1 lucidity every 2 rounds (14 total).",
    "一声长鸣把附近的梦都引向声源；近处的则被震住一回合。":
        "A long blast draws nearby dreams toward the source; those close by are stunned for a round.",
    "5 格内、且真能看见这束光的失控意识视距减半：墙挡住的不会被闪，贴得近的也仍能看见你——这是削弱视野，不是隐身。":
        "Unbound minds within 5 tiles that can actually see the flash have their sight halved; walls spare the hidden, and close ones still make you out — this is dimmed vision, not invisibility.",
    "把脚下的格子擦得比诚实还滑。": "Wipes the cell underfoot slicker than honesty.",
    "最后一点温度刚好够点燃邻居。": "The last warmth is just enough to ignite a neighbour.",
    "拧到一半的发条，把附近的梦拖进慢放：3 格内的失控意识慢 3 回合。":
        "A half-wound spring drags nearby dreams into slow motion: unbound minds within 3 cells are slowed for 3 rounds.",
    "贴身释放，把相邻的目标连同撞墙的代价一起送走。":
        "Released at contact, sending an adjacent target away along with the cost of hitting a wall.",
    "架在身前，8 回合内下一次指向你的打击会被原路退回。":
        "Raise it before you: the next blow aimed at you within 8 rounds returns the way it came.",
    "贴着液面滑行，一段直线不再耗时。":
        "Skim the liquid surface: one straight stretch costs no time.",
    "踩上去会落空一个行动，崩解度也随之松了一点。":
        "Stepping on it wastes an action, and dissolution slackens slightly.",
    "两次成像叠在同一格里：下一个正式动作不消耗时间，但只存一次、5 回合内没用就褪。":
        "Two exposures on one frame: the next proper action costs no time, but it holds only once and fades if unused within 5 rounds.",
    "顺着它走一步，梦还没来得及记下时间。":
        "Follow it one step before the dream has time to note it.",
    "笔尖磨得锋利，写出的每个字都带刃。近战与弹体伤害 +1。":
        "The nib is sharpened; every word it writes has an edge. Melee and projectile damage +1.",
    "一击钉穿三层梦。伤害 +2。": "One strike nails through three layers of the dream. Damage +2.",
    "补丁摞着补丁，梦的爪子抓不透。受到的心智创伤 -1。":
        "Patch upon patch; no dream claw gets through. Mind trauma taken -1.",
    "工坊里带来的旧围裙，硬得像另一层皮肤。受到的清醒创伤 -1。":
        "An old workshop apron, hard as a second skin. Lucidity trauma taken -1.",
    "正面是梦，反面也是梦。每次击破失控意识，崩解度额外推进 2。":
        "Dreams on the face, dreams on the back. Each stray consciousness you break pushes dissolution 2 further.",
    "还剩一点电，够照亮一步之外。视野 +1。":
        "A little charge left — enough to light one step beyond. Vision +1.",
    "指尖露在外面，拾取东西快得像没拿过。拾取显化物不耗时。":
        "Fingertips exposed; you pick things up as if you never held them. Picking up manifestations costs no time.",
    "拧螺丝的手感还在。修缮效果额外 +30。":
        "Your feel for the screwdriver remains. Repair effect +30.",
    "盖在弹道上的印，谁都拦不住。弹体穿透 +1。":
        "A seal stamped on the trajectory; nothing can stop it. Projectile pierce +1.",
    "从最多三个未习得的通用构想中选择一个永久习得。可查看完整效果、想象力费用与冷却；取消不消耗。全部习得后恢复10点想象力。":
        "Permanently learn one of up to three unlearned general conceptions. Review full effects, imagination cost and cooldown; cancelling costs nothing. Restores 10 imagination if all are learned.",
    "随机永久习得一个未习得的通用构想。全部习得后恢复10点想象力。":
        "Permanently learn a random unlearned general conception. Restores 10 imagination if all are learned.",
    "{name}｜想象力 {cost}｜冷却 {cooldown} 回合\n{description}":
        "{name} | Imagination {cost} | Cooldown {cooldown} turns\n{description}",
    "选择一个构想永久习得；取消不消耗。":
        "Choose one conception to learn permanently; cancelling costs nothing.",
    "构想已全部习得，书卷化作 10 点想象力。":
        "All conceptions are learned. The book becomes 10 imagination.",
    "永久习得构想：{name}。": "Permanently learned conception: {name}.",
    "书卷已失效，未消耗。": "This book offer is no longer valid; nothing was consumed.",
    # ---- 主动构想 ----
    "火花构想": "Spark Conception",
    "望远构想": "Farsight Conception",
    "迟缓构想": "Slow-wave Conception",
    "显影构想": "Develop Conception",
    "回响构想": "Echo Conception",
    "推斥构想": "Repulse Conception",
    "镜面构想": "Mirror Conception",
    "曝光构想": "Exposure Conception",
    "在想象里划一根火柴：点燃相邻的可燃材料。":
        "Strike a match in your mind: ignite adjacent flammable material.",
    "把视平线推向远处：视野 +3，持续 5 回合。":
        "Push the horizon away: vision +3 for 5 rounds.",
    "把周围五格的梦拖进泥沼：范围内异象移动迟缓 5 回合。":
        "Drag the dreams within five cells into a mire: anomalies inside move slowly for 5 rounds.",
    "凭空冲洗一张底片：以自身为中心半径 5 的地形永久显影。":
        "Develop a negative from nothing: terrain within radius 5 is permanently developed.",
    "虚构一声长鸣：半径 14 的异象被引向声源，近处的被震住一回合。":
        "Invent a long blast: anomalies within radius 14 are drawn to the source, the nearest stunned for a round.",
    "把周围的梦推开：相邻异象被推出最多 2 格并承受 1 点创伤。":
        "Push the surrounding dream away: adjacent anomalies are shoved up to 2 cells and take 1 trauma.",
    "在身前立一面不存在的镜子：下一次指向你的打击被原路退回。":
        "Raise a mirror that isn't there: the next blow aimed at you is sent back the way it came.",
    "让所有看得见的异象过曝：视野内异象的视野减半 3 回合。":
        "Overexpose every visible anomaly: their vision is halved for 3 rounds.",
    # ---- 弹体 ----
    "直线弹体": "Line Projectile",
    "穿页弹体": "Page-piercing Projectile",
    "冲击弹体": "Impact Projectile",
    "折返弹体": "Return Projectile",
    "最稳定的直线弹体。": "The steadiest line projectile.",
    "穿过第一层坚实聚合物后仍保持方向。":
        "Keeps its heading after passing through the first solid aggregate.",
    "命中后把对象沿弹道方向推出。": "On hit, shoves the target along the trajectory.",
    "撞击低硬度表面后保留一次折返机会。":
        "Keeps one bounce after striking a low-hardness surface.",
    # ---- 事件 ----
    "圆环里藏着一条没有写完的路线。": "A route left unfinished hides in the ring.",
    "它坚持自己已经完成。": "It insists it is already finished.",
    "车票没有日期，站台却在催促。": "The ticket has no date, yet the platform hurries you.",
    "清醒的裂纹指向一片看不见的区域。": "The lucid crack points to an unseen region.",
    "雨声来自没有天线的机器。": "The rain comes from a machine with no antenna.",
    "灯亮起时，某段记忆允许被携带。":
        "When the lamp lights, a memory is allowed to be carried.",
    "最后一行拒绝出现。": "The last line refuses to appear.",
    "批注没有指向文字，而是指向你。":
        "The annotation points not at the text, but at you.",
    "机器停止后，时间才显出形状。":
        "Only when the machine stops does time show its shape.",
    "灰烬下的打火机": "Lighter under the Ash",
    "打火机还在烫，灰烬却不记得烧过什么。":
        "The lighter is still hot, but the ash remembers burning nothing.",
    "浴缸里的退潮": "Ebb in the Bathtub",
    "水退向一个不存在的地漏。": "The water recedes toward a drain that doesn't exist.",
    "药盒的最后一格": "Last Slot of the Pill Box",
    "星期日的格子被拆走了。": "Sunday's slot has been taken out.",
    "晕开的休止符": "Blurred Rest Note",
    "乐谱泡在水里，休止符最先消失。":
        "The score soaked in water; the rest notes vanish first.",
    "阁楼的折叠梯": "Folding Ladder to the Attic",
    "梯子放下来时，阁楼多出一层。":
        "When the ladder comes down, the attic gains a floor.",
    "窗外的站台比车慢。": "The platform outside moves slower than the train.",
    "静电里的电台": "Radio in the Static",
    "电流声排成了句子的形状。": "The hum of current lines up into the shape of a sentence.",
    "卷尺画出的房间的界线": "Room Line Drawn by the Tape",
    "卷尺拉到底，墙就照着它长。":
        "Pull the tape all the way out and the wall grows to match it.",
    "无声的图书馆": "Silent Library",
    "书架之间没有脚步声，书页自己在翻。":
        "No footsteps between the shelves; the pages turn themselves.",
    # ---- 洞察（描述） ----
    "首次回应异常地点后，下一次下潜额外恢复 1 点清醒度。":
        "After your first response to an anomaly site, the next descent restores 1 extra lucidity.",
    "携带惯用物时，坚实聚合物受到的穿透阻力降低 1。":
        "While a habitual tool is equipped, solid aggregate offers 1 less pierce resistance.",
    "首次进入警戒的异象不会在同一回合攻击。":
        "An anomaly that first enters alert will not attack in the same round.",
    "清醒度低于 50 时，远域覆写稳定半径增加 1 格。":
        "While lucidity is below 50, far-field overwrite's stable radius increases by 1.",
    "弥散印象遮挡视线的阈值提高。":
        "The threshold at which diffuse impressions obscure sight is raised.",
    "异常地点的观测记录会额外保存一条描述。":
        "Observation records of anomaly sites keep one extra description.",
    "想象力归零时仍可使用一次主动构想。":
        "Even at zero imagination you may use one active conception.",
    "每次首次解决强烈异象时恢复 2 点心智。":
        "The first time you solve an elite anomaly, restore 2 mind.",
    "尖啸瓷墙碎裂波及你时，恢复 3 点想象力。":
        "When a shrieking porcelain wall shatters and catches you, restore 3 imagination.",
    "崩解度不低于 50 后，其增长减半（向下取整）。":
        "Once dissolution reaches 50 or higher, its growth is halved (rounded down).",
    "液体格不再额外耗时，液体接触的迟滞对你无效。":
        "Liquid cells cost no extra time, and the sluggishness of liquid contact does not affect you.",
    "视野外的悬停格会显示它的类别（液态记忆或弥散印象），而非完全未知。":
        "Hovered cells outside your vision show their category (liquid memory or diffuse impression) instead of staying fully unknown.",
    "合唱团的攻击耗时减免上限降低 0.1，成群的攻击节奏被削弱。":
        "The choir's attack-time reduction cap falls by 0.1, and the attack rhythm of groups is weakened.",
    "双重曝光的残影在你的视野半径内显形为虚线轮廓，不再被伪装骗到。":
        "Double exposure's afterimages show as dashed outlines inside your vision radius, and disguises no longer fool you.",
    "拾取显化物不消耗时间。": "Picking up manifestations costs no time.",
    "辐射尘埃的辐射病对你无效。":
        "Radiation sickness from radiation dust does not affect you.",
    "液氮的冻僵对你无效。": "Liquid nitrogen's chill does not affect you.",
    "灼热蒸汽的灼伤对你无效。": "Scalding steam's burns do not affect you.",
    "镜面碎片与镜面架势的反伤 +1。":
        "Mirror shard and mirror stance reflect +1 damage.",
    "蜂蜜的清醒恢复上限翻倍。": "Honey's lucidity restoration cap is doubled.",
    "照彻期间异象被光钉住冻结 2 回合，而非追踪你。":
        "During illumination, anomalies are pinned by the light and frozen for 2 rounds instead of tracking you.",
    # ---- 层主题 ----
    "可辨认的房间": "Recognizable Rooms",
    "拼接的走廊": "Spliced Corridors",
    "回声平台": "Echo Platform",
    "无窗工作室": "Windowless Studio",
    "退色的展馆": "Faded Gallery",
    "未完成的边界": "Unfinished Boundary",
    # ---- 墙体（贴近效果 / 气息） ----
    "透明隔断": "Transparent Partition",
    "反光刺目": "Glare",
    "声响被吸收": "Sound Absorbed",
    "表面凝水": "Condensation",
    "燃料震颤": "Fuel Tremor",
    "纸味潮湿": "Damp Paper",
    "蜡味温热": "Warm Wax",
    "高频尖啸": "High-pitched Shriek",
    "空响": "Hollow Echo",
    "字句排列变动": "Shifting Type",
    "记忆沉淀的气味": "Scent of Settled Memory",
    "思绪的低语": "Whisper of Thought",
    "清凉的石头气息": "Cool Stone Air",
    "晶体嗡鸣": "Crystal Hum",
    "烛油的暖味": "Warm Candle Oil",
    "潮湿的云絮": "Damp Cloud Wisp",
    "米香": "Rice Aroma",
    "木头的干涩气味": "Dry Scent of Wood",
    "石面的凉意": "Coolness of Stone",
    "灯罩里透出一口暖息": "A Warm Breath from the Shade",
    "臭氧与金属的焦味": "Ozone and Scorched Metal",
    "余烬的暖味": "Warmth of Embers",
    "沉闷的金属闷响": "Dull Metal Thud",
    "咸涩的结晶": "Salt Crystals",
    # ---- 液体接触效果名（征兆 id 之外的展示名） ----
    "传导冲击": "Conductive Shock",
    "腐蚀创伤": "Acid Trauma",
    "心智修复": "Mind Mending",
    "悬浮": "Suspended",
    "月光": "Moonlight",
    "气体易感": "Gas Susceptible",
    "剥蚀墙体": "Wall Erosion",
    # ---- 气体吸入效果名 ----
    "毒性吸入": "Toxic Inhalation",
    "迟钝吸入": "Sedative Inhalation",
    "醉意吸入": "Drunken Inhalation",
    "遮蔽吸入": "Obscuring Inhalation",
    "可燃附着": "Flammable Coating",
    "回声扩散": "Echo Diffusion",
    "灼伤吸入": "Scalding Inhalation",
    "麻痹吸入": "Numbing Inhalation",
    "深度睡眠": "Deep Sleep",
    "清朗吸入": "Clarity Inhalation",
    "安眠吸入": "Poppy Inhalation",
    "褪黑吸入": "Melatonin Inhalation",
    "亢奋吸入": "Stimulant Inhalation",
    "辐射病吸入": "Radiation Inhalation",
    # ---- 植物 ----
    "低草": "Short Grass",
    "高丛": "Tall Thicket",
    "发光地衣": "Glowing Lichen",
    "蘑菇": "Mushroom",
    # ---- 征兆效果（灰色注释，随 `\` 展开显示） ----
    "残余电流在意识里打转：每 2 回合清醒度 −1；与静电尘同处时每回合额外 −1。":
        "Residual current swirls in your mind: lucidity −1 every 2 rounds; an extra −1 per round while sharing a cell with static dust.",
    "镇静溶液压住了惊惶：持续期间心智不再减少。":
        "The sedative solution stills the panic: mind no longer decreases while it lasts.",
    "酸蚀液仍在啃噬你的意识：每回合失去 1 点心智。":
        "Acid etch keeps gnawing at your mind: lose 1 mind each round.",
    "粘稠的纸浆拖住脚步：移动额外耗时 +0.5，两步最多被拖慢 1 回合。":
        "Thick pulp drags at your steps: moves cost an extra +0.5, so two steps are slowed by at most 1 round.",
    "稀释记忆的余温：持续期间每 2 回合恢复 1 点想象力（不再于接触瞬间回复）。":
        "The warmth of diluted memory: restores 1 imagination every 2 rounds while it lasts (no longer on contact).",
    "泪滴溶液托住心智：滞留时每回合恢复 1 点心智，每层上限 5。":
        "Tear solution holds your mind up: while you linger, restore 1 mind each round, up to 5 per layer.",
    "水蒸气润开了想象：每 3 回合恢复 1 点想象力。":
        "Steam loosens the imagination: restores 1 imagination every 3 rounds.",
    "毒气渗进意识：每 2 回合失去 1 点心智。":
        "Poison gas seeps into the mind: lose 1 mind every 2 rounds.",
    "麻醉雾压住动作：移动额外耗时 +1。":
        "Anesthetic fog weighs down your motion: moves cost an extra +1.",
    "酒气熏得意识发飘：每 4 回合清醒度 −1，攻击额外耗时 +0.3。":
        "Alcohol fumes set the mind adrift: lucidity −1 every 4 rounds, attacks cost an extra +0.3.",
    "酒精蒸气熏得更透：每 2 回合清醒度 −1，攻击额外耗时 +0.5；身上残留的可燃蒸气依然见火就着。":
        "Alcohol vapor seeps deeper: lucidity −1 every 2 rounds, attacks cost an extra +0.5; the flammable vapor left on you still catches fire.",
    "弥散印象糊住视线：视野缩到 65%（比例跨族取最小倍率，不相乘）。":
        "Diffuse impression smears your sight: vision shrinks to 65% (ratios take the smallest multiplier across the family; they do not multiply).",
    "身上残留可燃气体：紧邻火焰时每回合额外承受 1 点清醒创伤。":
        "Flammable gas clings to you: take 1 extra lucidity trauma per round while adjacent to flame.",
    "灰尘塞住视野：每 3 回合清醒度 −1，视野 −1。":
        "Dust clogs your sight: lucidity −1 every 3 rounds, vision −1.",
    "你的动静被雾放大：声音传播半径翻倍，异象更容易被引来。":
        "The fog amplifies your noise: sound carries twice as far, and anomalies are drawn in more easily.",
    "灼热蒸汽烫着意识：每 2 回合清醒度 −1。":
        "Scalding steam burns the mind: lucidity −1 every 2 rounds.",
    "静电让四肢发木：移动额外耗时 +0.2。":
        "Static numbs your limbs: moves cost an extra +0.2.",
    "催眠雾让你每一次行动都额外多沉 1 回合；雾中的异象同样被困住。":
        "Hypnotic fog makes every action sink 1 extra round; anomalies caught in the fog are trapped as well.",
    "浓缩咖啡因的还款期：持续 10 回合，每 2 回合清醒度 −1。":
        "The espresso debt: lasts 10 rounds, lucidity −1 every 2 rounds.",
    "纸浆与静电尘的粘滞仍在积累，随时会拖慢你的下一步。":
        "Pulp and static dust keep accumulating; your next step may be slowed at any moment.",
    "底片上的第二次成像先于时间完成：下一个动作不消耗时间。":
        "The second exposure finishes ahead of time: your next action costs no time.",
    "下一次移动不耗时。": "Your next move costs no time.",
    "沿液体直线移动不耗时。": "Moving in a straight line along liquid costs no time.",
    "镜面碎片架在你和梦之间：下一次指向你的打击将被原路退回。":
        "A mirror shard stands between you and the dream: the next strike aimed at you is sent straight back.",
    "挂在梦的墙上的承载物将替你承受下一次打击。":
        "The burden hung on the dream's wall will take the next strike for you.",
    "灯塔透镜仍在替你照亮远处：视野 +3（下潜后的前 3 回合）。":
        "The lighthouse lens still lights the distance: vision +3 (for the first 3 rounds after descending).",
    "全图被照亮：你看得见所有异象，它们也看得见你（仅在本层生效）。":
        "The whole map is lit: you see every anomaly, and they see you too (this layer only).",
    "忘川水漫过意识：分不清周围，视野范围 −2。":
        "Lethe water floods the mind: near and far blur together, vision −2.",
    "无念黑渊吞掉了记忆：无法使用或装配行囊与携带意象，物品名称都变成问号。":
        "The Abyss of No-Thought swallows memory: bag items cannot be used or equipped, and their names all become question marks.",
    "流动月光替你照亮四周：视野范围翻倍。":
        "Flowing moonlight lights your surroundings: vision doubled.",
    "身体被放大：挤过 1 格宽的缝隙时移动耗时翻倍，仍然挤不过门，受到的心智创伤减半。":
        "Your body is enlarged: squeezing through a 1-cell gap doubles that move's time, doors still refuse you, and mind trauma taken is halved.",
    "看见所有意象的位置与形态——每个失控意识的位置与种类都如实显形（连伪装也看穿），代价是它们也同时看见了你的位置。":
        "See the position and form of every image — each stray consciousness is revealed exactly as it is, disguise included — at the cost of them seeing your position too.",
    "蜂蜜裹住伤口：每 2 回合恢复 1 点清醒度（每层上限 6）；上方生物移速减半。":
        "Honey coats the wound: restores 1 lucidity every 2 rounds (up to 6 per layer); creatures above move at half speed.",
    "熔化的时间拖住一切行动：所有行动耗时加倍。":
        "Molten time drags at every action: all actions cost double.",
    "清醒香气驱散迷醉：免疫醉意/麻痹/迟钝/深眠/安眠/褪黑。":
        "Clarity aroma clears intoxication: immune to drunk / numb / sedated / deep sleep / poppy sleep / melatonin.",
    "安眠香让想象力自然恢复翻倍，但每一次行动都会多沉 1 回合。":
        "Sleep incense doubles natural imagination recovery, but every action sinks 1 extra round.",
    "褪黑素雾让心智自然恢复翻倍，但每一次行动都会多沉 1 回合。":
        "Melatonin mist doubles natural mind recovery, but every action sinks 1 extra round.",
    "液氮冻住了关节：移动额外耗时 +1。":
        "Liquid nitrogen freezes your joints: moves cost an extra +1.",
    "辐射尘埃在体内堆积：每 3 回合心智与清醒度各 −1。铅板邻格可屏蔽。":
        "Radiation dust builds up inside you: mind and lucidity each −1 every 3 rounds. A lead plate in an adjacent cell blocks it.",
    "咖啡因气让移速提升一半，并免疫深眠与醉意。":
        "Caffeine vapor raises move speed by half and grants immunity to deep sleep and drunkenness.",
    # ---- 观测面板里带剩余量的动态效果文案 ----
    "浓缩咖啡因的还款期：每 2 回合清醒度 −1（剩约 {turns} 回合）。":
        "The espresso debt: lucidity −1 every 2 rounds (about {turns} rounds left).",
    "沿液体直线移动不耗时（剩 {count} 格）。":
        "Moving in a straight line along liquid costs no time ({count} cells left).",
    "{item}挂在梦的墙上，将替你承受下一次打击。":
        "{item} hangs on the dream's wall and will take the next strike for you.",
    "全图被照亮（剩 {turns} 回合）：你看得见所有异象，它们也看得见你。":
        "The whole map is lit ({turns} rounds left): you see every anomaly, and they see you too.",
    # ---- 征兆来源（Excel 用；界面上暂不显示，一并补齐） ----
    "接触导电液态记忆": "Touch conductive liquid memory",
    "接触镇静溶液": "Touch sedative solution",
    "接触酸蚀液": "Touch acid etch",
    "接触纸浆": "Touch paper pulp",
    "接触纸浆或静电尘": "Touch paper pulp or static dust",
    "接触稀释记忆": "Touch diluted memory",
    "接触泪滴溶液": "Touch tear solution",
    "接触忘川水": "Touch Lethe water",
    "接触流动月光": "Touch flowing moonlight",
    "接触彩虹牛奶": "Touch rainbow milk",
    "接触灵视之血": "Touch blood of true sight",
    "接触蜂蜜": "Touch honey",
    "接触熔化的时间": "Touch molten time",
    "接触液氮": "Touch liquid nitrogen",
    "吸入毒气": "Inhale poison gas",
    "吸入麻醉雾": "Inhale anesthetic fog",
    "吸入酒气": "Inhale alcohol fumes",
    "吸入酒精蒸气": "Inhale alcohol vapor",
    "吸入遮蔽弥散印象": "Inhale obscuring impression",
    "吸入可燃气体": "Inhale flammable gas",
    "吸入回声雾": "Inhale echo fog",
    "吸入灼热蒸汽": "Inhale scalding steam",
    "吸入静电尘": "Inhale static dust",
    "吸入催眠雾": "Inhale hypnotic fog",
    "吸入清醒香气": "Inhale clarity aroma",
    "吸入安眠香": "Inhale sleep incense",
    "吸入褪黑素雾": "Inhale melatonin mist",
    "吸入辐射尘埃": "Inhale radiation dust",
    "吸入咖啡因气": "Inhale caffeine vapor",
    "使用浓缩咖啡因": "Use espresso shot",
    "使用双重曝光底片": "Use double-exposure negative",
    "使用松脱的缝线": "Use loose thread",
    "使用湿折页": "Use wet fold",
    "使用镜面碎片": "Use mirror shard",
    "携带挂钩并携带易逝物": "Equip the hook and carry a perishable",
    "携带灯塔透镜并下潜": "Equip the lighthouse lens and descend",
    "解决空心灯塔": "Resolve the hollow lighthouse",
    "备用（暂未启用）": "Reserved (not yet enabled)",
    # ---- 携带意象 / 易逝物：名称（描述在上面「物品描述」区已有） ----
    "削尖的钢笔": "Sharpened Pen",
    "沉重的订书机": "Heavy Stapler",
    "打补丁的睡衣": "Patched Pajamas",
    "皮革围裙": "Leather Apron",
    "磨亮的硬币": "Burnished Coin",
    "夜灯的电池": "Night-light Battery",
    "缺指的手套": "Fingerless Gloves",
    "小号螺丝刀": "Small Screwdriver",
    "蜡封图章": "Wax Seal Stamp",
    "破损的书卷": "Damaged Tome",
    "断裂的残页": "Torn Page",
    # ---- 格子详情：环境对象的功能介绍（键 = materials/descriptions.py 的描述文本） ----
    # ---- 地板介绍 ----
    '梦最普通的地面：平整、开放，是全层高低起伏的基准面——没有特殊效果，可以放心行走。': "The dream's plainest ground: even and open, the layer's baseline for height — no special effect, safe to walk on.",
    '踩上去微微下陷的软质地面：软垫护住植被，踩过不会把高丛踩折；行走与流速不受影响。': 'Soft ground that gives a little underfoot: the padding protects vegetation, so tall grass is never trampled flat; walking and liquid flow are unaffected.',
    '布满磨砂颗粒的地面：颗粒拖住液滴，本格的液体扩散得比别处慢一半，但不会被堵住；行走不受影响。': 'A floor covered in fine grit: the grains drag on droplets, so liquid in this tile spreads at half the usual rate — slowed down, but never blocked; walking is unaffected.',
    '能映出人影的光亮地面：站在上面时四周的光多反射一点回来，视野 +1。': 'A glossy floor that mirrors your shape: standing on it bounces a little more light back, sight +1.',
    '吞掉声音的哑光地面：站在上面时你发出的声响半径 −2（至少 1），异象更难循声找到你。': 'A matte floor that swallows sound: standing on it cuts the radius of the noise you make by 2 (minimum 1), so anomalies have a harder time tracking you by ear.',
    '什么都没来得及生长的地面：梦在这里还没画完，一片平整空白——植物无法在其上生长。': "Ground where nothing has grown yet — the dream hasn't finished painting here: flat and blank, and plants cannot grow on it.",
    '承托墙体与一切结构的地基，无法徒手清除。': 'The substrate that carries walls and every structure; it cannot be cleared by hand.',
    '积着液态记忆的地面，深浅随液量变化。': 'Ground pooled with liquid memory, its depth rising and falling with the liquid.',
    '被弥散印象占据的地面，气味先于视野抵达。': 'Ground claimed by a diffuse impression; the smell arrives before the sight does.',
    # ---- 墙体介绍 ----
    '最普通的梦之墙体：坚硬、厚重，挡住移动与视线。': "The dream's most ordinary wall: hard, thick, blocking both movement and sight.",
    "梦游者留下的木桌：1 格高的固体，不能穿过，但平整的桌面可以承载物品与事件地点；站在相邻格点击桌面即可取走上面的东西。": (
        "A wooden table left by sleepwalkers: a one-tile-high solid you cannot walk through, but its flat top "
        "holds items and event sites; stand adjacent and click it to take what's on it."
    ),
    "厚重的石砌台座：1 格高的固体，不能穿过，台面稳稳托着物品与事件地点；站在相邻格点击石台即可取走上面的东西。": (
        "A heavy stone platform: a one-tile-high solid you cannot walk through, steadily holding items and event "
        "sites; stand adjacent and click it to take what's on it."
    ),
    "带木纹的地面材质：木质吸湿易干，本格液体每 20 回合多蒸掉 1 点；总是成片铺开。": "Wood-grained flooring: wood drinks damp and dries fast, so liquid here loses 1 extra point every 20 turns; always grows in patches.",
    "松软多孔的地面材质：会一点点吸走本格的液体（每 2 回合 1 点，不成雾），积在它上面的液体会缓缓渗干；总是成片铺开。": "Soft, porous flooring: it soaks the liquid in its tile away drop by drop (1 point every 2 turns, without mist), so anything pooled on it seeps dry by degrees; always grows in patches.",
    "冷硬的金属板地面：表面光滑，液体在其上流得更畅（流出量 ×3）；总是成片铺开。": "Cold metal plating: its smooth surface lets liquid run freer (outflow x3); always grows in patches.",
    "隐隐发烫的赤色地面：余温烘得本格液体多蒸掉 2 点、气体多散 1 点，并不造成伤害；总是成片铺开。": "Faintly warm scarlet flooring: the residual heat evaporates 2 extra points of liquid and disperses 1 extra point of gas each interval, and deals no damage; always grows in patches.",
    '透明而脆的隔断：挡移动不挡视线；被破坏时炸开碎屑，划伤相邻的单位。': 'A transparent, brittle partition: blocks movement but not sight; when broken it bursts into shards that cut adjacent units.',
    '会晃眼的镜面墙：贴着它时反光刺目，只该贴空气生成；被破坏后腾起黑烟。': 'A dazzling mirrored wall: standing beside it stings the eyes; it only forms against open air, and billows black smoke when broken.',
    '吸掉周围声音的哑光墙体，靠近时连呼吸都变轻。': 'A matte wall that drinks in sound; even your breathing softens as you approach.',
    "规整到不像梦的六边形晶格：极硬极韧，却能被一格格推着走（推不动回不来）。": "A hexagonal lattice too regular for a dream: extremely hard and tough, yet it can be pushed one cell at a time (push only — it never comes back).",
    "遇强则强的非牛顿墙：子弹与远程攻击全被它软软吞掉，只有近身才啃得动。": "A non-Newtonian wall that hardens under force: bullets and ranged attacks sink in without a trace; only close combat can chip it.",
    "铺满一整片的绒面：完全吞掉脚步声，火焰也烧不着它。": "A wall-to-wall velvety surface: it swallows every footstep, and fire cannot burn it.",
    "光滑的冰：沿这个方向一路滑到头，撞上什么才停下——只花一个回合。": "Slick ice: you slide in that direction until you hit something — the whole glide costs only one turn.",
    "地面嵌着缓缓亮起的星图：站上去看得更远。": "The floor is inlaid with a slowly brightening star chart: sight extends while you stand on it.",
    "散落的纸页铺成的地面：可燃，烧完变回普通聚合物。": "A floor of scattered loose pages: flammable; once burned it reverts to plain aggregate.",
    "灰白的月尘：每 2 回合从脚下的格子里吸走 1 点气体。": "Pale grey moon dust: every 2 rounds it draws 1 point of gas out of the cell beneath it.",
    "黑白格随回合交替闪烁：站在上面的生物每回合有 10% 随机获得一种常见增益。": "Black and white squares that alternate each round: creatures standing on them have a 10% chance per round of a random common boon.",
    "隔火的层压材料：火焰无法在它上面蔓延。": "Layered fire insulation: flames cannot spread across it.",
    "超流的银色液体：扩散无视地势，流经之处火焰当场熄灭，也不在身上留下任何征兆。": "A superfluid silver liquid: it flows regardless of terrain, snuffs out flames it touches, and leaves no portent behind.",
    "浅层梦境的清凉香草：拔除后得到「薄荷露」（恢复心智并冲开迟滞与麻痹的欠账）。":
        "A cool herb of the shallow dream: uprooting yields Mint Dew (restores mind and clears sluggishness and numbness).",
    "修表匠的遗摊": "The Watchmaker's Abandoned Stall",
    "夜班查房": "Night Ward Rounds",
    "天文台的旧课桌": "The Observatory's Old Desk",
    "干涸的许愿池": "The Dry Wishing Pool",
    "快照亭": "The Photo Booth",
    "梦的邮局": "The Dream Post Office",
    "泡胀的信箱": "The Waterlogged Letterbox",
    "电梯里的音乐": "Music in the Elevator",
    "衣柜后的门": "The Door Behind the Wardrobe",
    "镜子里的面试": "Interview in the Mirror",
    "信箱里塞满没有地址的信，墨迹在水里舒展。": "The letterbox crams with unaddressed letters; the ink unfurls in the water.",
    "幕布后面没有相机，照片却一张张吐出来。": "There is no camera behind the curtain, yet photos keep sliding out.",
    "抽屉里的星图标注着一颗不存在的星。": "The star chart in the drawer marks a star that does not exist.",
    "摊位上摆着一排都停在三点整的表。": "A row of watches, all stopped at exactly three o'clock, lines the stall.",
    "柜台上盖着邮戳：昨日未达，退回。": "The counter bears a postmark: undelivered yesterday, returned to sender.",
    "池底铺满硬币，每一枚都朝上。": "The pool bottom is paved with coins, every one face-up.",
    "电梯停在两个楼层之间，音乐还在播。": "The elevator is stuck between floors; the music keeps playing.",
    "衣柜背面有一圈门铰链的印子。": "The back of the wardrobe bears the imprint of door hinges.",
    "走廊尽头的病房亮着一盏夜灯，护士站没有人。": "A night lamp glows at the end of the ward; the nurses' station stands empty.",
    "镜中人递来一份没有问题的问卷。": "Your reflection hands over a questionnaire with no questions on it.",
    "精神观测家": "Mind Observer",
    "催眠师": "The Hypnotist",
    "小魔鬼": "The Little Devil",
    "拾荒的委托人": "The Scavenger Patron",
    "提着铜制观测镜的旅人：专门收集梦里才有的罕见念头。": "A traveler with a brass spyglass: collects rare thoughts found only in dreams.",
    "怀表在指间画圈的温和声音：她说睡眠也是一种交易。": "A gentle voice drawing circles with a pocket watch: sleep, she says, is also a currency.",
    "尾巴打着节拍的小个子：合约藏在每一句玩笑里。": "A small figure keeping time with its tail: every joke hides a clause.",
    "燃烧瓶": "Molotov Bottle",
    "雷管胶囊": "Detonator Capsule",
    "镁光火柴": "Magnesium Match",
    "信号焰火": "Signal Flare",
    "点火手套": "Ignition Gloves",
    "凤凰羽衣": "Phoenix Feather Robe",
    "爆破扳指": "Blast Ring",
    "纵火者怀表": "Arsonist's Pocket Watch",
    "装着燃油的玻璃瓶：投掷（Q）后在落点周围燃起一片火海；原地使用则烧到自己脚下。": "A glass bottle of fuel: throw (Q) it to splash fire across the landing zone; use in place and it burns at your own feet.",
    "捏起来微微发烫的胶囊：投掷后在落点引爆；威力 3、半径 1（爆破扳指可加大半径）。": "A capsule warm to the touch: detonates where it lands; power 3, radius 1 (the Blast Ring widens it).",
    "烧起来白得刺眼的镁条：使用即进入投掷瞄准，落点十字五格点燃本来就可燃的材料；也可在物品菜单里选「原地点燃」，不经瞄准直接在脚下释放——脚下有燃料时，你自己也站在那片火中央。高浓度可燃气会被引爆。": "A magnesium strip that burns blinding white: using it opens throw aiming, and the five cells of a cross at the landing point ignite whatever was already flammable; the item menu also offers Ignite Here to release it underfoot without aiming — with fuel underfoot you are standing in the middle of that fire too. Dense gas detonates.",
    "撕开即燃的焰火：视野内的异象被强光晃得睁不开眼（致盲 5 回合）。": "A flare that ignites as you tear it: anomalies in sight are blinded for 5 rounds.",
    "指节内侧嵌着燧石：近战与弹体命中后，目标所在格被点燃。": "Flint set into the knuckles: melee and projectile hits ignite the target's cell.",
    "织物里衬着不肯熄的暖意：站在火焰里不再受到清醒创伤。": "Lined with warmth that refuses to die: standing in fire no longer costs clarity.",
    "内侧刻着膨胀曲线的戒指：你投掷的爆炸物与烈焰新星的半径 +1。": "A ring engraved with an expansion curve: your thrown explosives and flame nova gain +1 radius.",
    "表盘上的刻度全是燃点：你点燃的每一处火焰都烧得更旺（点燃强度 +1）。": "Every mark on the dial is a kindling point: every fire you light burns hotter (+1 ignition strength).",
    "引爆构想": "Detonation Concept",
    "火墙构想": "Firewall Concept",
    "烈焰新星构想": "Flame Nova Concept",
    "隔空擦出一粒火星，射向视野内最近的可燃材料——高浓度气体会被当场引爆。": "Strike a spark across the void at the nearest flammable material in sight — dense gas detonates on the spot.",
    "在身前立起一排凭空燃烧的火墙（5 格），烧退追上来的影子。": "Raise a freestanding wall of flame before you (5 cells), scorching back the shadows that catch up.",
    "以自己为圆心炸开一朵火环：半径 2、威力 3 的爆炸并引燃周围（自己不受爆炸伤害）。": "Burst a ring of flame centered on yourself: radius 2, power 3 explosion that also ignites the surroundings (you take no explosion damage).",
    "背着大包裹的沉默身影：委托书写得比人话还多。": "A silent figure under a huge pack: the commission forms speak more than she does.",
    "叶脉里凝着琥珀色的光：拔除时散出少量晨霜清气，吸入者每 3 回合恢复 1 点清醒。":
        "Amber light pools in its veins: uprooting spills a little morning-frost air, giving whoever breathes it 1 lucidity every 3 rounds.",
    "闻一闻就忘记不安的小白花：拔除后沾染「忘忧」——持续期间心智不再减少。":
        "A small white flower that quiets unease: uprooting attaches Worry-Free — mind no longer decreases while it lasts.",
    "菌盖像彩色的玻璃，夜里自己发光（可燃性却出奇地低）；拔除得到「彩玻碎片」，踩碎时清脆地响一声（散出少量呢喃）。":
        "A mushroom whose cap is like colored glass, glowing at night (surprisingly fireproof); uprooting yields a Glass Shard, and stepping on it breaks with a clear chime (spilling a little whispering).",
    "叶片之间有人在交换秘密：拔除后沾染「呢喃」——你的声音替它们传播（声音半径 ×3）。":
        "Someone trades secrets between its fronds: uprooting attaches Whispering — your voice carries theirs (sound radius ×3).",
    "规整的六边形晶格": "A tidy hexagonal lattice",
    "受压时骤然变硬": "Hardens under pressure",
    "受压发电的地板：站上去每回合蓄 1 层电，离开每回合泄 1 层；攒满 10 层会放电，给周围 3×3 的意识体（包括自己）造成少量清醒创伤。": "A pressure-charging floor: standing on it builds 1 charge per round, leaving bleeds 1 per round; at 10 charges it discharges, dealing light clarity trauma to every consciousness in 3×3 (yourself included).",
    '渗水的蓝色囊壁：破坏后放出一滩水与一股水蒸气，相邻格也会被水浸湿。': 'A weeping blue sac wall: breaking it releases a pool of water and a puff of steam, soaking adjacent cells.',
    '一碰就出事的燃料墙：破坏后泄漏一大团可燃气体，并当场爆炸。': 'A fuel wall eager to misbehave: breaking it leaks a large cloud of flammable gas and detonates on the spot.',
    '受潮发胀的纸墙：低矮脆弱，破坏后在原地留下一滩易燃的纸浆，点火可成连锁。': 'A water-swollen paper wall: low and fragile; breaking it leaves a pool of flammable pulp — a spark can chain it.',
    '封存记忆的蜡墙：热敏易融，与火焰相邻时每回合融去 2 点完整度，融尽即消失。': 'A wax wall sealing memories: heat-sensitive, it loses 2 integrity per turn beside flame and vanishes once melted through.',
    '高频震颤的瓷墙：破坏时尖啸着炸出一片灰尘云，碎瓷会划伤相邻的所有单位。': 'A porcelain wall humming at high frequency: breaking it screams, bursts into a dust cloud, and its shards cut every adjacent unit.',
    '中空的轻质墙体：可以徒手推倒，几乎没有抵抗。': 'A hollow, lightweight wall: push it over bare-handed with almost no resistance.',
    '由活字排成的墙：破坏后黑墨流出，字句四散。': 'A wall built of movable type: breaking it spills black ink and scatters the sentences.',
    '低矮的地面容器：完整时把封存的液体锁在格内不外流，推倒后液体随流动散出。': 'A low ground vessel: while intact it locks its liquid inside the cell; once toppled the liquid flows away.',
    '低矮的地面容器：完整时把封存的气体锁在格内不消散，推倒后气体逸散。': 'A low ground vessel: while intact it locks its gas inside the cell; once toppled the gas escapes.',
    '幻觉空间的主墙体：比浅梦的墙更硬、更高、更难撼动。': "The phantom space's main wall: harder, taller, and far harder to shake than shallow-dream walls.",
    '散发清凉气息的石头：相邻格上的单位（不分敌我）被持续清除醉意、麻痹、迟钝、深眠、遮蔽、安眠与褪黑素类征兆，沾不上也留不住。': 'A stone breathing cool air: units on adjacent cells, friend or foe alike, are continuously cleared of drunkenness, numbness, sedation, deep sleep, obscuration, sleep-scent drowse, and melatonin portents — they cannot take hold or linger.',
    '储存气体的晶簇：持续吸储周围 3×3 格内的气体（上限 100、只存一种），被破坏后封存的气体尽数涌出。': 'A gas-storing crystal cluster: it continuously siphons gas from the surrounding 3×3 cells (cap 100, one kind only); when broken, every stored gas bursts out.',
    '凝固的烛泪堆成的柱子，带着一点点余温；被相邻的火焰点着后燃尽，原地留下灰烬并淌出一滩熔融蜡烛。': 'A pillar of hardened candle drips, still holding a trace of warmth: lit by adjacent flame it burns away, leaving ash and a pool of molten candle wax.',
    '吸收脚步声的木质枕条：生物可以直接走过、不留声响；被火烧到会化进一片安眠香。': 'A wooden sleeper that absorbs footsteps: creatures walk straight through without a sound; burned, it dissolves into a waft of sleep scent.',
    '可以穿行的云絮：生物能直接从它上面走过，液体却被它挡住、无法漫过。': 'A wisp of cloud you can walk through: creatures pass right over it, while liquid is held back and cannot flow across.',
    '一堆喷香的米：低矮松散，可徒手推开；被火烧成一片催眠的青烟。': 'A heap of fragrant millet: low, loose, and pushable by hand; burned, it becomes a haze of hypnotic smoke.',
    '沉闷的铅制隔板：又重又哑。相邻格上的单位不会染上辐射病，已有的辐射病也会被它屏蔽消除。': 'A lead partition, heavy and mute: units on adjacent cells cannot contract radiation sickness, and any they already have is shielded away.',
    '半透明的盐晶：坚硬而咸涩，可以隔晶看到对面；任一相邻格积了水就会溶解消失。': 'A semi-transparent salt crystal: hard and briny, and you can see through it; it dissolves away as soon as water pools in any adjacent cell.',
    '烧尽后的余烬堆，一碰就散。': 'A pile of burnt-out ashes that scatters at a touch.',
    '本层的尽头：梦在这里拒绝继续，任何力量都撼不动。': 'The edge of this layer: the dream refuses to continue here, and nothing can move it.',
    '会开合的咽喉：踏上即开、离开即关，无论开合都不透视线。': 'A throat that opens and closes: it opens as you step on it and shuts behind you, and it blocks sight whether open or closed.',
    # ---- 液态记忆介绍 ----
    '最普通的液体：无味无性，只会向低处流。': 'The plainest liquid: tasteless, inert, flowing only downhill.',
    '发酵的暗红液体：浸过的地方会留下酒气。': 'A fermented dark-red liquid: places it soaks take on the smell of drink.',
    '浓稠的黑色液体：流动缓慢，沾上很难洗净。': 'A thick black liquid: slow-moving and hard to wash off.',
    '会导电的记忆：站在里面会遭受传导冲击。': 'A conductive memory: standing in it invites a conducted shock.',
    '安神的绿色液体：踩进去获得镇静，心智不再流失。': 'A calming green liquid: stepping in grants sedation, and the mind stops eroding.',
    '易燃的油状液体：遇火即燃，蔓延得很快。': 'An oily flammable liquid: ignites at a spark and spreads fast.',
    '腐蚀性的酸液：接触会造成腐蚀创伤。': 'A corrosive acid: touching it inflicts corrosion trauma.',
    '黏稠的纸浆：行动迟滞，还极易着火。': 'Sticky paper pulp: it slows your every move and catches fire easily.',
    '显影记忆的药水：浸过的地面会永久显影，视野外也可见地形。': 'A memory-developing reagent: ground it soaks stays developed forever, its terrain visible even out of sight.',
    '被稀释的温热记忆：踩上去觉得暖，恢复一点点清醒。': 'A diluted warm memory: stepping in feels comforting and restores a little lucidity.',
    '温热的泪滴：站在里面缓缓修复心智。': 'Warm teardrops: standing in them slowly mends the mind.',
    '饮之忘忧的水：接触会陷入遗忘，看不清周围。': 'Water of forgetting: touching it brings oblivion, blurring everything around.',
    '发着微光的月光：接触后被月色笼罩，夜里也能视物。': 'Glowing moonlight in liquid form: touch it and moonlight wraps you, letting you see in the dark.',
    '黏稠的时间本身：接触后行动、攻击都被拖慢。': 'Time itself, thickened: touch it and both movement and attack slow down.',
    '色彩打旋的奶液：接触后感知被放大。': 'A swirling mix of colored milk: touch it and your senses enlarge.',
    '腥红的血液：接触后获得诅咒灵视，看见视野外的轮廓。': 'Crimson blood: touch it and gain cursed sight, seeing outlines beyond your vision.',
    '黏住的甜蜜：行动大幅迟滞，但火焰不喜欢它。': 'Sticky sweetness: it slows you drastically, though fire cares little for it.',
    '轻逸的悬浮之液：踩进去身体变轻，悬浮而行。': 'A weightless levitating liquid: step in and your body lightens, drifting as it moves.',
    '滚烫的蜡液：易燃，凝固前一直烫脚。': 'Molten wax: flammable, and it scalds your feet until it sets.',
    '沉重的水银：站上去时本格气体的触发浓度降低，毒气更容易生效。': "Heavy mercury: standing on it lowers the trigger threshold of the cell's gas, letting poison take hold more easily.",
    '极寒的低温液体：接触会被冻僵。': 'A bitterly cold cryogenic liquid: touching it freezes you stiff.',
    '侵蚀性极强的流体：无需生物携带，会自行渗进相邻墙体的缝隙剥蚀它们，连坚硬聚合墙也挡不住。': 'An aggressively eroding fluid: needing no carrier, it seeps into the seams of adjacent walls and eats them away — even hardened polymer cannot resist it.',
    # ---- 弥散印象介绍 ----
    '温热的白雾：无害，只是糊住视野。': 'Warm white vapor: harmless, just blurring your view.',
    '完全不透光的浓烟：隔着它什么都看不见。': 'Thick smoke that admits no light at all: nothing can be seen through it.',
    '有毒的黄绿雾气：吸入会中毒。': 'A poisonous yellow-green haze: breathing it poisons you.',
    '令人迟钝的雾：吸入后反应变慢。': 'A numbing fog: inhale it and your reactions dull.',
    '发酵的酒味：吸入会醉，脚步不稳。': 'The fume of ferment: inhale it and drunkenness unsteadies your steps.',
    '遮蔽感官的紫雾：吸入后看不清周围。': 'A purple fog that veils the senses: inhale it and your surroundings blur.',
    '一点就着的气体：附着在身上，遇火燃烧。': 'A gas that lights at the first spark: it clings to you and burns at a flame.',
    '呛人的尘云：透尘看物，视野打对折。': 'A choking dust cloud: you see through it at half your sight.',
    '传声的雾：声音在雾里扩散得更远。': 'A sound-carrying fog: voices travel much farther inside it.',
    '滚烫的蒸汽：吸入会造成灼伤。': 'Scalding steam: inhaling it burns you.',
    '带电的浮尘：吸入会被麻痹。': 'Charged drifting dust: inhale it and your limbs go numb.',
    '深眠之雾：吸入会直接睡着。': 'A deep-sleep fog: inhale it and you drop asleep on the spot.',
    '提神的香气：吸入后更清醒。': 'A clarifying aroma: inhale it and lucidity sharpens.',
    '助眠的香气：吸入后昏昏欲睡。': 'A lulling aroma: inhale it and drowsiness settles in.',
    '催困的雾：吸入后困意压顶。': 'A sleep-heavy mist: inhale it and weariness presses down.',
    '亢奋的气雾：吸入后行动加速。': 'A jittery caffeinated haze: inhale it and your actions quicken.',
    '纯净的酒气：吸入会酩酊，且极易被点燃。': 'Pure alcohol vapor: inhale it to get roaring drunk, and it lights at the smallest flame.',
    '发着绿光的尘埃：吸入会得辐射病。': 'Green-glowing dust: inhale it and radiation sickness takes hold.',
    # ---- 植物介绍 ----
    '齐踝的梦之草：可以踩过，遇液体消失、见火燃尽。': 'Ankle-high dream grass: walk over it freely; it dissolves in liquid and burns at a flame.',
    '齐腰的深草：遮挡视线，被踩踏后无声折成低草。': 'Waist-deep thicket: it blocks sight, and silently flattens to low grass when trampled.',
    '亮黄色的发光地衣：照亮周围一圈，并把无遮挡方向的视距延长几格。': 'Bright-yellow glowing lichen: it lights the surrounding ring and extends your sight a few tiles along unobstructed lines.',
    '棕色的蘑菇：液体与火焰都破坏不了它。': 'A brown mushroom: neither liquid nor fire can harm it.',

    # ---- 图鉴：物品/携带意象「作用说明」的机制描述（键 = 描述文本） ----
    '穿戴时解锁「发射」；脱下后重新上锁。': 'While equipped, firing is unlocked; taking it off locks firing again.',
    '掷到落点才爆炸：半径内造成创伤、把目标推开一格、削弱坚实聚合物并引燃可燃材料；玩家自己站在半径里照样吃清醒创伤。': 'Bursts where it lands: trauma inside the radius, targets shoved one cell, solid aggregate chewed down and flammable material caught alight — stand in the radius yourself and you take lucidity trauma too.',
    '点燃脚下的液态记忆或弥散印象（需足量），原地升起火焰。': 'Ignites the liquid memory or diffuse impression underfoot (enough of it required), raising a flame in place.',
    '站在导电介质上使用：沿四邻连通的介质放电（四格内、最多二十格），被击中的失控意识这一拍慢一步；余电在介质上停留五回合，敌我都要躲。': 'Use while standing in a conductive medium: the discharge walks connected cells (up to four away, twenty at most) and the struck unbound minds lose a step; the residual charge lingers five rounds — friend and foe alike had better move.',
    '使用后恢复与效力相等的想象力。': 'When used, restores imagination equal to its power.',
    '使用后获得可再装的弹体充能。': 'When used, gains a reusable projectile charge.',
    '拾取时存进梦的记忆碎片，跨局保留（最多 3 条）；碎片是「可拆卸的洞察」，提供征兆免疫、环境适应或少量上限提升。': 'When picked up it is stored as a dream memory fragment, kept across runs (up to 3); fragments are detachable insights that grant portent immunity, environmental adaptation, or a small cap increase.',
    '使用后修补相邻受损的墙体。': 'When used, repairs damaged walls in adjacent cells.',
    '使用后恢复与效力相等的心智。': 'When used, restores mind equal to its power.',
    '使用后恢复与效力相等的清醒度。': 'When used, restores lucidity equal to its power.',
    '携带在依附物时，自动把第一件易逝物挂上梦的墙，替你承受下一次打击。': "While worn as an accessory, it automatically hangs the first expendable on the dream's wall to take the next hit for you.",
    '携带在自我表层：自身脚步与普通道具声径 −2、不再显示贴近提示；不改异象视野。': 'Worn on the self-surface: −2 sound radius for your footsteps and ordinary items, and no proximity hints; anomaly vision is unchanged.',
    '携带在依附物：3 格内的失控意识移动更迟缓。': 'Worn as an accessory: unbound minds within 3 cells move more sluggishly.',
    '携带在依附物：下潜后的前 3 回合获得「透镜余晖」（视野 +3）。': 'Worn as an accessory: grants Lens Afterglow (sight +3) for the first 3 rounds after descending.',
    '使用后读出到悬停格的最短步数（按全知口径计算）。': 'When used, reports the shortest step count to the hovered cell (computed with full knowledge).',
    '使用后同时恢复清醒度与想象力。': 'When used, restores both lucidity and imagination.',
    '五五开：要么心智 +15，要么心智 −8 且清醒度 −3。': 'Fifty-fifty: either mind +15, or mind −8 and lucidity −3.',
    '使用后想象力 +效力，但接下来 10 回合每 2 回合扣 1 点清醒度。': 'When used, imagination +power, but 1 lucidity is paid every 2 rounds for the next 10 rounds.',
    '使用后恢复心智，并清空迟滞与麻痹的欠账。': 'When used, restores mind and clears lingering sluggish and numb debts.',
    '使用后获得「振奋」：每 2 回合恢复 1 点清醒度。': 'When used, grants Invigorated: +1 lucidity every 2 rounds.',
    '使用后发出声波引诱周围的失控意识，近处 1 格的会被震停。': 'When used, emits a sound pulse that lures nearby unbound minds; those within 1 cell are stunned.',
    '让看得见这束光的失控意识视距减半五回合（使用那一拍也算在内）：墙挡住的不会被闪，不看眼睛的目标免疫。': 'Every unbound mind that can see the flash has its sight halved for five rounds (the turn you use it counts); walls spare the hidden, and things that do not look with eyes are immune.',
    '使用后把脚下格子变滑：踩上的失控意识移动更慢（持续到换层）。': 'When used, makes your cell slippery: unbound minds stepping on it move slower (until the layer changes).',
    '使用后点燃相邻一格的可燃液体或气体。': 'When used, ignites one adjacent cell of flammable liquid or gas.',
    '使用后拖慢效力范围内失控意识的动作（持续时间按物品定义，发条半卷为 3 回合）；只作用于敌对关系，NPC 不受影响。': 'When used, slows the actions of unbound minds within its power radius; the duration comes from the item definition (3 rounds for the half-wound spring). Only hostile relations are affected; NPCs are not.',
    '落点向八个方向各抛一束火星，最远 3 格，遇墙即止；不铺油，只点燃沿途本来就可燃的材料。与燃烧瓶的 3×3 火场分工不同：它靠半径覆盖，烟花靠方向穿透。': 'Flings one spark down each of eight directions from the landing point, up to 3 cells, stopping at walls; it lays no fuel and only ignites material that was already flammable. It differs from the 3x3 sheet of a molotov: the bottle covers an area, the fireworks pierce along lines.',

    '三格内（曼哈顿距离）最近的一个看得见的接收器机关按响一次：机关门开合、显影方尖点亮、囚笼栅栏升降、弹射座弹射、灌注阀灌注、共鸣报警器报警。同距离时优先当前朝向那一格；三格内没有这样的机关就拒绝，且不消耗键帽。': 'Presses the nearest receiver mechanism you can see within three cells (Manhattan distance): a logic door opens or closes, a reveal obelisk lights, a cage fence rises or falls, a launcher fires, a valve pours, an alarm sounds. On a tie the cell you are facing wins; with no such mechanism in range the press is refused and the keycap is not consumed.',
    '落点 3×3 点燃，十字五格的燃油不一次铺满：落地先淌一层 20 单位，之后第 1、2 回合各再淌一层，合计 60（每格约 12，火比燃烧瓶更匀更久）。后续几层只加燃油、不重复点燃，伤害只有落点那一次；异种液体的格子不会被焦油顶掉，防火层铺不上。': 'The 3x3 lights at the landing, but the five-cell cross does not take all its fuel at once: twenty units pour on landing, then another twenty on each of rounds 1 and 2, sixty in all (about twelve per cell — a more even, longer fire than a molotov). The later pours only add fuel and never re-ignite, so the landing is the only damage; a cell holding another liquid is not displaced, and fireproof floors take none.',    '使用后铃声按真实声路传播（墙体衰减、听觉上限、阈值），听得到的失控意识慢 5 回合；听不到的不受影响。': 'When used, the bell travels the real sound path (wall attenuation, hearing range, threshold): unbound minds that can hear it are slowed for 5 rounds; those that cannot are unaffected.',
    '使用后击退相邻的目标并造成 1 点创伤。': 'When used, knocks back an adjacent target and deals 1 trauma.',
    '使用后获得一次格挡。': 'When used, gains one parry.',
    '使用后获得沿液面直线免费行走的步数。': 'When used, gains free straight-line steps across liquid.',
    '使用后崩解度 −效力。': 'When used, dissolution −power.',
    '使用后获得一次免费行动。': 'When used, gains one free action.',
    '使用后获得一次免费移动。': 'When used, gains one free move.',
    '携带在手中意象：攻击创伤 +效力。': 'Worn in the hand-image slot: attack trauma +power.',
    '携带后承受的心智创伤 −效力。': 'While equipped, mind trauma taken −power.',
    '携带后承受的清醒创伤 −效力。': 'While equipped, lucidity trauma taken −power.',
    '携带后每次解决失控意识，崩解推进 +效力。': 'While equipped, resolving an unbound mind grants dissolution +power.',
    '携带后视野 +效力。': 'While equipped, sight +power.',
    '携带后拾取不耗时。': 'While equipped, picking things up takes no time.',
    '携带后修缮量 +效力。': 'While equipped, repair amount +power.',
    '携带后弹体穿透 +效力。': 'While equipped, projectile penetration +power.',
    '使用后习得一个尚未学会的主动构想；全部习得后化作 10 点想象力。': 'When used, learns one unlearned active ability; once all are learned it becomes 10 imagination.',
    '使用后以自身为中心、半径＝效力的地形永久显影：视野外也看得见地形。': 'When used, permanently develops terrain in a radius around you equal to its power: the terrain stays visible even out of sight.',
    '使用后清除噩梦、虚无与遗忘（含无念黑渊的失忆）一类的控制类负面征兆。': 'When used, clears control-type negative portents such as nightmare, voidness and forgetting (including the Abyss of No-Thought amnesia).',
    '携带后承受的心智创伤与清醒创伤各 −效力。': 'While equipped, both mind trauma and lucidity trauma taken −power.',
    '携带后攻击的基础耗时 −0.2×（效力÷2）：零头记账，平均每 5 次攻击省 1 回合。': 'While equipped, base attack cost −0.2 × (power ÷ 2); the fraction is carried as debt, so on average every 5 attacks save 1 round.',
}

# Bounded material residue, combat FX rebalance (2026-10-08).
EN_CONTENT.update({
    'X → 方向键 → Enter': 'X → arrows → Enter',
    '按 X 观察，用方向键移动 ? 辅助选中区，按 Enter 前往可达位置。\n直接左键点远处也可寻路；行走中任意键取消，该按键只刹停。':
        'Press X, move the observation cursor with arrows, then Enter walks to a reachable tile.\nA left click also starts navigation. Any key while walking only stops the route.',
    '电痉挛': 'Electric spasm',
    '被连通电场击中': 'Struck by a connected electric field',
    '短促电流绊住关节：移动额外耗时 +0.8，仅维持 1 回合。': 'A short current locks the joints: move time +0.8 for only 1 round.',
    '电场': 'Electric field',
    '余电还会持续 {n} 回合，每回合创伤 1；离开导电格可避开。': 'Residual charge lasts {n} more rounds, dealing 1 trauma per round. Leave conductive tiles to avoid it.',
    '借脚下水、导电液态记忆或金属地面的电压，沿四邻连通的介质放电：最远四格、最多二十格，被击中的失控意识这一拍慢一步。余电在介质上停留五回合，谁踩上算谁的——自己也及时离开。': 'The voltage underfoot — water, conductive liquid memory or metal flooring — discharges along connected cells: up to four tiles away, twenty at most, and every unbound mind it strikes loses a step. The leftover charge sits in the medium for five rounds and bites whoever steps in it, including you.',
    '每 2 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。静电尘中每回合额外清醒 −1。': 'Every 2 rounds: Lucidity -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 6 rounds to wear off. Static dust adds 1 Lucidity damage per round',
    '每 2 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。': 'Every 2 rounds: Mind -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 5 rounds to wear off.',
    '每 2 回合：想象力 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 7 回合退净。': 'Every 2 rounds: Imagination +0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 7 rounds to wear off.',
    '每 2 回合：心智 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 7 回合退净。': 'Every 2 rounds: Mind +0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 7 rounds to wear off.',
    '每 3 回合：想象力 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。': 'Every 3 rounds: Imagination +0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 6 rounds to wear off.',
    '每 2 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。': 'Every 2 rounds: Mind -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 6 rounds to wear off.',
    '每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。攻击耗时 +0.3。': 'Every 4 rounds: Lucidity -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 6 rounds to wear off. Attack time +0.3',
    '每 2 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。攻击耗时 +0.5。': 'Every 2 rounds: Lucidity -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 6 rounds to wear off. Attack time +0.5',
    '每 3 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。视野 -1。': 'Every 3 rounds: Lucidity -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 5 rounds to wear off. Sight -1',
    '每 2 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。': 'Every 2 rounds: Lucidity -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 5 rounds to wear off.',
    '每 2 回合：想象力 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。额外耗时 +1。': 'Every 2 rounds: Imagination +0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 6 rounds to wear off. Extra time +1',
    '每 5 回合：心智 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。额外耗时 +1。': 'Every 5 rounds: Mind +0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 6 rounds to wear off. Extra time +1',
    '每 3 回合：心智 -0.5、清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 7 回合退净。': 'Every 3 rounds: Mind -0.5, Lucidity -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 7 rounds to wear off.',
    '每 3 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。行动速度 ×1.5。': 'Every 3 rounds: Lucidity -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 5 rounds to wear off. Action speed x1.5',
    '每 2 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 3 回合退净。': 'Every 2 rounds: Mind -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 3 rounds to wear off.',
    '每 2 回合：心智 -1（越往深处越重）。离开材料还会缠 2 回合，再花 3 回合退净。': 'Every 2 rounds: Mind -1 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 3 rounds to wear off.',
    '每 3 回合：想象力 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。视野 -4。': 'Every 3 rounds: Imagination -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 6 rounds to wear off. Sight -4',
    '每 2 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。崩解每回合 +1。': 'Every 2 rounds: Lucidity -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 6 rounds to wear off. Dissolution +1 per round',
    '每 3 回合：清醒 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 7 回合退净。': 'Every 3 rounds: Lucidity +0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 7 rounds to wear off.',
    '每 3 回合：心智 -1（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。视野 +1。': 'Every 3 rounds: Mind -1 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 5 rounds to wear off. Sight +1',
    '每 2 回合：想象力 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。视野 -1。': 'Every 2 rounds: Imagination +0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 5 rounds to wear off. Sight -1',
    '每 3 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。行动速度 ×1.4。': 'Every 3 rounds: Lucidity -0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 5 rounds to wear off. Action speed x1.4',
    '每 4 回合：想象力 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。': 'Every 4 rounds: Imagination +0.5 (it weighs more the deeper you go). It clings for 2 rounds after you leave, then takes 6 rounds to wear off.',
    '余火：离开火焰后每 2 回合清醒 −1；站在火焰中仅结算直接灼伤，入水熄灭。': 'Embers: lose 1 Lucidity every 2 rounds after leaving fire. Flames apply direct burn damage only; water extinguishes embers.',
})

# 携带意象联想盘（2026-10-09，docs/equipment-dream-board-redesign.md 与
# docs/superpowers/specs/2026-10-09-equipment-grammar-design.md）。
EN_CONTENT.update({
    "携带意象 · 联想盘": "Carried Images - Association Board",
    "握持": "Holding",
    "（空手）": "(empty-handed)",
    "（握持）": "(held)",
    "生效": "active",
    "备用": "spare",
    "待触发": "armed",
    "未成句": "unformed",
    "就绪": "ready",
    "CD {n}": "CD {n}",
    "联想盘 {used}/{total} · 握持 {focus}": "Board {used}/{total} - holding {focus}",
    "{paths} 条通路 · {broken} 处未成句 · 编辑": "{paths} paths - {broken} unformed - edit",
    "{endpoint} → {piece}　{tail}": "{endpoint} -> {piece}  {tail}",
    "接梦：还没有连出通路——在盘面上铺接梦线接到插片。":
        "Dream link: no path yet - lay dream threads across the board to reach a chip.",
    "命中端": "Hit port",
    "受击端": "Hurt port",
    "接触端": "Touch port",
    "构想端": "Conceive port",
    "湿润门": "Wet Gate",
    "缓冲片": "Buffer Chip",
    "移涌片": "Surge Chip",
    "电吻片": "Spark Chip",
    "留白门": "Blank Gate",
    "留声片": "Echo Chip",
    "分流片": "Splitter Chip",
    "余温片": "Ember Chip",
    "传声片": "Voice Chip",
    "联想反馈·{label}：在 {x},{y} 留下一点余温（强度 {strength}）。":
        "Association feedback - {label}: a little residual heat is left at {x},{y} (strength {strength}).",
    "联想反馈·{label}：{x},{y} 响起一次轻声（{reached} 个失控意识转头）。":
        "Association feedback - {label}: a soft sound rings once at {x},{y} ({reached} unruly minds turn to look).",
    "联想反馈·{label}：把这次事件存了下来，{due} 回合时释放。":
        "Association feedback - {label}: this event is stored away, to be released at turn {due}.",
    "这副联想盘放不下：{reason}": "This association board cannot be laid out: {reason}",
    "联想盘已整理：占地 {used}/{total} 格。": "Association board tidied: {used}/{total} cells used.",
    "盘面没有变化，不消耗行动。": "Nothing changed on the board; no action spent.",
    "行囊装不下卸回来的意象，整理没有发生。":
        "The satchel cannot hold what would come off the board; the tidy-up did not happen.",
    "{item}已经在联想盘上了。": "{item} is already on the association board.",
    "{item}没有登记形状，暂用兼容形状 {shape}。":
        "{item} has no registered shape; using the compatible shape {shape} for now.",
    "联想盘上没有能放下 {item} 的合法位置。": "No legal spot on the association board can fit {item}.",
    "那件意象不能作为握持焦点。": "That image cannot be the held focus.",
    "已经握着它了。": "You are already holding it.",
    "那件意象不在盘上。": "That image is not on the board.",
    "{item}没有这个词义。": "{item} has no such sense.",
    "旧五栏的这副组合在 8×6 盘面上放不下，迁移已中止（原存档保留）。":
        "This old five-slot combination does not fit the 8x6 board; migration aborted (the original save is kept).",
    "旧存档的五栏组合在 8×6 联想盘上放不下：装备仍留在行囊里，请重新整理上盘。":
        "The old save's five-slot set does not fit the 8x6 association board: the gear stays in your satchel, please lay it out again.",
    "联想反馈·{label}：{target} 吃了一记微弱放电（1 点完整度）。":
        "Association feedback - {label}: {target} takes a faint discharge (1 integrity).",
    "联想反馈·{label}：把 {amount} 单位{kind}涌向相邻格。":
        "Association feedback - {label}: {amount} units of {kind} surge into an adjacent cell.",
    "联想反馈·{label}：下一次对应创伤减少 1（保留 {until} 回合）。":
        "Association feedback - {label}: the next matching trauma is reduced by 1 (held {until} rounds).",
    # ---- 梦中梦·千禧园（2026-10-10）：Y2K 主题 EN ----
    "蓝砖墙": "XP Blue Brick",
    "千禧树": "Millennium Tree",
    "木门": "Wooden Door",
    "色块墙·红": "Color Block Wall (Red)",
    "色块墙·橙": "Color Block Wall (Orange)",
    "色块墙·蓝": "Color Block Wall (Blue)",
    "白块窗": "White Block Window",
    "传真墙": "Fax Wall",
    "灯箱墙": "Lightbox Wall",
    "弹窗墙": "Popup Wall",
    "磁带墙": "Tape Wall",
    "摇杆柱": "Joystick Post",
    "打印机墙": "Printer Wall",
    "蓝屏终端": "BSOD Terminal",
    "XP 蓝白砖缝": "XP blue-and-white mortar lines",
    "永远的下午四点": "Forever four in the afternoon",
    "垃圾传真：贴近暴露位置": "Junk fax: standing close reveals your position",
    "关不掉的弹窗": "The popup you cannot close",
    "倒带迟滞：贴近移动变慢": "Rewind lag: moving close slows you down",
    "可推动": "Pushable",
    "卡纸了": "Paper jam",
    "你的电脑遇到问题，需要重新启动": "Your computer ran into a problem and needs to restart",
    "蓝屏守夜人": "BSOD Warden",
    "它守着一块永远亮着的死屏，屏上的进度条一百年没走完。":
        "It guards a screen that died forever on, its progress bar stuck for a hundred years.",
    "倒带幽灵": "Rewind Ghost",
    "一段倒着放的录像：它总在你到达之前，先回到你出发的地方。":
        "A tape played backwards: it always returns to where you started before you get there.",
    "传呼精灵": "Pager Sprite",
    "腰间别着一台永远在震动的传呼机：哔——哔——找你有事。":
        "A pager that never stops buzzing hangs at its hip: beep — beep — someone is looking for you.",
    "迪斯科残响": "Disco Echo",
    "一场散场二十年的舞会还在它头顶继续，光斑扫过之处皆是碎彩。":
        "A dance floor that closed twenty years ago still rages above its head; its light dots scatter broken color.",
    "雪花观众": "Static Viewer",
    "一台没有信号的电视里坐着一位观众，从头到尾没有换过台。":
        "Inside a signal-less TV sits one viewer who has never changed the channel.",
    "软盘收藏家": "Floppy Collector",
    "它收藏每一张写坏的软盘，并把坏档案归档到你的口袋里。":
        "It collects every corrupted floppy and files the bad sectors into your pocket.",
    "屏保气泡": "Screensaver Bubble",
    "上世纪的屏幕保护程序还在漫天飘——里面偶尔闪过一行褪色的字。":
        "Last century's screensaver still drifts everywhere — a faded line of text blinks inside now and then.",
    "指针追猎者": "Cursor Hunter",
    "一支没有主人的箭头光标，永远指向它决定要点击的东西。":
        "An ownerless arrow cursor, forever pointing at whatever it has decided to click.",
    "开机音合唱": "Startup Chorus",
    "数十年前每一次开机的启动音，在这里叠成了永不停歇的和声。":
        "Every boot chime from decades ago layered into a harmony that never stops.",
    "断链漫游者": "Deadlink Roamer",
    "404。它走过的链接全都失效，但它自己永远能重新加载。":
        "404. Every link it walks goes dead, yet it can always reload itself.",
    "弹窗推销员": "Popup Peddler",
    "「恭喜您获得大奖！」——点掉一个，它还会再开三个。":
        "'Congratulations, you won a prize!' — close one and three more open.",
    "核心执念·千年虫": "Core Obsession: Millennium Bug",
    "它害怕 2000 年，于是把梦停在了 1999 年 12 月 31 日。你是来送它过零点的。":
        "It fears the year 2000, so it froze the dream on December 31, 1999. You are here to see it across midnight.",
    "56k 猫": "56k Modem",
    "调制解调器握手完成的一瞬，世界开始缓冲式加速。":
        "The instant the modem handshake completes, the world starts buffering into overdrive.",
    "调制解调器的握手音。听一会儿，紧绷的神经松开了。":
        "The handshake screech of a dial-up modem. Listen a while and your nerves unknot.",
    "像素碎片": "Pixel Scrap",
    "千禧园里散落的坏点。拼起来，还能看见一点旧日的安稳。":
        "Dead pixels scattered across the garden. Piece them together and a little old comfort shows through.",
    "屏保气泡水": "Screensaver Soda",
    "喝下去，气泡从脊椎往上飘——清醒 +11。":
        "Drink it and bubbles float up your spine — Lucidity +11.",
    "拨号音": "Dial Tone",
    "56k 握手完成的一瞬，世界开始缓冲式加速。":
        "The instant the 56k handshake completes, the world starts buffering into overdrive.",
    "未读消息 99+": "Unread 99+",
    "永远清不完的红点。焦虑推着你往前：崩解推进 +1。":
        "The red badge you can never clear. Anxiety pushes you forward: dissolution +1.",
    "水晶机箱挂饰": "Crystal Case Charm",
    "机箱前面板上的亚克力小水晶。晃一晃，静电都绕着走（心智创伤 −2、清醒创伤 −2）。":
        "An acrylic trinket from a case front panel. Give it a swing and static steers clear (mind trauma −2, lucidity trauma −2).",
    "留言板签名": "Guestbook Signature",
    "在梦的留言板上签个名：「到此一游」。写完心里踏实一点。":
        "Sign the dream's guestbook: 'was here'. Signing it settles the heart a little.",
    "闪存盘": "USB Drive",
    "拔下来之前先「安全弹出」。能随身灌一点液体带走。":
        "Eject safely before unplugging. It can carry a little liquid for you.",
    "宽带圣杯": "Broadband Grail",
    "千年虫的巢穴深处流出的一条永远在线的带宽。思维流畅：攻击基础耗时 −0.4。":
        "An always-on bandwidth flowing from the Bug's lair. Mental fluency: base attack time −0.4.",
    "倒带迟滞": "Rewind Lag",
    "磁带倒卷的吱嘎声缠住脚步：移动额外耗时 +0.2。":
        "The whir of rewinding tape winds around your steps: +0.2 move time.",
    # ---- 梦中梦·千禧园 M5（2026-10-10）：材料描述补齐 ----
    "老猫握手时的沙沙杂音：米色的声浪在园子里弥散。只是背景音，不改变任何读数。":
        "The scratchy static of an old modem handshake: beige sound-waves drift across the park. Pure ambience — it changes nothing.",
    "退役年代的蓝白砖墙：砖缝里还印着那两个字——必胜。":
        "A blue-and-white brick wall from a retired era: the mortar still reads WIN.",
    "永远下午四点的树：树冠把阳光滤成旧显示器的暖黄色。":
        "A tree locked at 4 PM forever: its canopy strains sunlight into the warm yellow of an old monitor.",
    "木屋的门：和普通门一样踏上即开、离开即关，开合都不透视线。":
        "The cabin door: steps open it, leaving closes it, and it blocks sight whether open or shut.",
    "体育场看台的红色座椅块：漆面亮得像刚出厂那天。":
        "A red stadium seat block: the paint gleams like the day it left the factory.",
    "体育场看台的橙色座椅块：一排排坐满了看不见的观众。":
        "An orange stadium seat block: rows packed with unseen spectators.",
    "体育场看台的蓝色座椅块：客队席，永远安静。":
        "A blue stadium seat block: the away section, forever silent.",
    "半透明的白块窗：隔着它还能望见外面的草地。":
        "A translucent white block window: the lawn outside is still visible through it.",
    "垃圾传真机墙：贴近时嗡鸣作响，把你的位置播报给 6 格内没察觉你的异象。":
        "A junk-fax wall: up close it whirs, broadcasting your position to unaware anomalies within 6 tiles.",
    "透光的灯箱墙：箱面上的广告早褪成一片暖黄。":
        "A backlit lightbox wall: its ad has long faded into a warm yellow glow.",
    "关不掉的弹窗墙：拆掉时弹出一封「未读消息 99+」。":
        "A popup wall you can't close: breaking it pops out an 'Unread 99+'.",
    "磁带墙：贴近时倒带的吱嘎声缠上脚步（移动 +0.2）。":
        "A tape wall: up close the rewind whine winds around your steps (+0.2 move time).",
    "可以推着走的摇杆柱：街机厅的遗物，推它挡路或开路。":
        "A joystick post you can push: an arcade relic — shove it to block or clear a path.",
    "卡纸的打印机墙：拆掉时在原地淌出一滩纸浆。":
        "A jammed printer wall: breaking it spills a puddle of pulp on the spot.",
    "零点体育场中央的主机：「你的电脑遇到问题，需要重新启动」。拆它，里面的东西就会醒。":
        "The tower at the center of Zero-Hour Stadium: 'Your PC ran into a problem and needs to restart.' Break it, and what lives inside wakes up.",
    "齐踝的蒲草，草尖永远指向下午四点的太阳：踩过会被拂得脚步发沉（移动 +0.5）。":
        "Ankle-high reeds whose tips forever point at the 4 PM sun: walking through leaves your steps heavy (+0.5 move time).",
    "贴水生长的低丛，叶尖挂着一串小气泡：液面漫过也不散。":
        "Low growth hugging the water, beaded with tiny bubbles: it holds even when the water rises over it.",
})



# 环境介绍的文风修订（2026-10-12）。
EN_CONTENT.update({
    '平整的浅色地面，脚步落下时没有回声。': 'A flat, pale floor. Your footsteps leave no echo.',
    '脚底轻轻陷下去，又被托住；草丛隔着软垫，踩过也不折。': 'The floor sinks gently underfoot, then holds you up. Its soft cushion keeps the grass from breaking.',
    '细砂硌着鞋底，液滴挂在颗粒间，流得比别处慢。': 'Fine grit presses against your soles. Droplets cling between the grains and flow more slowly.',
    '地面亮得像刚擦过，低头能看见人影，四周也显得更清楚。': 'The floor gleams as if freshly wiped. Your reflection lies below, and the surroundings look clearer.',
    '鞋底落下，声音却没有跟上；靠近这片哑光地面，呼吸也轻了。': 'Your feet land, but the sound never follows. Even breathing seems quieter over this dull floor.',
    '一片平整的空白，连一根草也没有长出来。': 'A flat blank expanse where not even one blade of grass has grown.',
    '木纹沿着地面延伸，水迹渗进去，很快只剩一圈浅印。': 'Wood grain runs across the floor. Wet marks soak in and soon leave only pale rings.',
    '细孔密密铺在脚下，积水一点点渗下去，不见水汽升起。': 'Tiny pores cover the floor. Pooled water seeps away without a wisp of steam.',
    '冷硬的金属板连成一片，液体贴着光滑表面迅速滑开。': 'Cold metal plates join into a sheet. Liquid slides quickly over their smooth surface.',
    '赤色地面烘着鞋底，水汽从脚边升起。': 'The crimson floor heats your soles, raising steam around your feet.',
    '镜面反光刺得人睁不开眼，砸碎时会冒出黑烟。': 'The reflected glare makes your eyes water. Breaking the mirror wall releases black smoke.',
    '暗白的菌盖贴着地面，像一小片没有温度的月色。液体与火焰都毁不掉它。': 'A pale white cap lies close to the floor, like a small patch of cold moonlight. Neither liquid nor fire destroys it.',
    '暖褐的菌盖鼓起，底下留着一圈阴影。液体与火焰都毁不掉它。': 'A warm brown cap rises above a ring of shadow. Neither liquid nor fire destroys it.',
    '绿液漫过鞋底，纷乱的念头渐渐安静；环境引起的心智流失也停了。': 'Green liquid washes over your soles. Scattered thoughts settle, and environmental mind loss stops.',
    '温热的液体里漂着模糊的旧影，浸在其中，想象力慢慢恢复。': 'Blurred old images drift through warm liquid. While immersed, your imagination slowly recovers.',
    '酒浆里沉着蜜，琥珀色的液面比红酒厚重，甜味迟迟不散。': 'Honey settles in amber wine, thickening it and leaving a sweetness that lingers.',
    '浓墨凝在地上，像一张忘了揭下的底片，几乎不再流动。': 'Thick ink lies on the ground like an abandoned photographic plate, barely flowing.',
    '酸液裹着熔金翻滚，热气里带着刺鼻的蚀味。': 'Acid rolls around molten metal. The rising heat carries a sharp, corrosive smell.',
    '暗红血迹封在黏蜡里，火苗一近，蜡面就亮起来。': 'Dark red blood is sealed in sticky wax. The surface lights up when a flame approaches.',
    '浮灰粘在蜂蜜里，积成灰黄色的膏，舀起时拖着细丝。': 'Dust caught in honey forms a grey-yellow paste that trails thin threads when lifted.',
    '灰白雾掠过，记住的地形也淡下去，片刻后才重新清楚。': 'Grey-white fog passes through. Remembered terrain fades too, then becomes clear again after a while.',
    '紫尘悬在眼前，远处轮廓变模糊，脑海里却不断浮出新的形状。': 'Purple dust hangs before your eyes. Distant outlines blur while new shapes rise in your mind.',
    '青雾贴着皮肤，细细刺痒；电流经过时刺痛更重，遇火也会燃烧。': 'Blue-green fog prickles against your skin. Passing current hurts more, and fire ignites the mist.',
    '橙色蒸汽吸进胸口，动作忽然轻快，清醒却一点点耗去。': 'Orange steam fills your chest. Your movements grow quick and light as lucidity slowly drains.',
    '暗色气团漫过，连脚步声也消失了，远处听不到这里的动静。': 'Dark gas rolls over you. Even footsteps fall silent; distant listeners hear nothing from here.',
    '粉雾里的虹光不停转动，眼前景物愈发错乱，梦却散得更快。': 'Rainbow light turns inside pink mist. The scene twists further out of shape as the dream dissolves faster.',
    '门缝里渗出冷风，吹得眼前轮廓偏斜，远处更难辨认。': 'Cold air seeps through a doorway, bending outlines and making distant things harder to distinguish.',
    '米色声浪里断续响着拨号与握手声，像旧电脑等着接通网络。': 'Waves of beige sound carry broken dial tones and modem handshakes, like an old computer waiting to connect.',
    '雾里有人压低嗓子说话。吸入以后，你的声音却传得格外远。': 'Someone whispers inside the mist. After breathing it in, your own voice carries unusually far.',
    '细小的孢子飘进眼里，周围暗下去，脑海中的形状也渐渐散开。': 'Tiny spores drift into your eyes. The surroundings dim, and the shapes in your mind slowly scatter.',
    '酸雾擦过脸颊，梦的边缘开始溶化，清醒随之流失。': 'Acid mist brushes your cheeks. The edges of the dream dissolve, taking lucidity with them.',
    '胸口忽然沉了一下，熟悉的噩梦已经贴到身上。': 'Your chest suddenly feels heavier. A familiar nightmare has already clung to you.',
    '黄绿瘴气又厚又刺鼻，隔着它，近处的人影也模糊。': 'The yellow-green miasma is thick and acrid. Even nearby figures blur behind it.',
    '雾中只剩断断续续的低语，孢子和噩梦都不见了，视线伸不进去。': 'Only broken whispers remain in the fog. Spores and nightmares have vanished, and sight cannot reach inside.',
    '青白微光悬在空中，细小电花沿着雾气闪动。': 'Blue-white light hangs in the air. Small sparks flicker along the mist.',
})

EN_CONTENT.update({
    '黑色花瓣透出暗紫微光。贴近或拔下它，月色就跟着你，视野增加四格。': 'Dark purple light shines through black petals. Come close or pluck it, and moonlight follows you, extending sight by four cells.',
    '小白花的香气很轻。拔下以后，惊惶也轻了，心智流失减半。': 'The small white flower has a faint scent. After plucking it, fear grows lighter and mind loss is halved.',
    '胶液拖住脚底：每步多耗时 0.15 回合；各种迟滞合计最多多耗时 0.5 回合。': 'Glue holds your soles: each step takes 0.15 rounds longer. Combined slowing adds at most 0.5 rounds per step.',
})

# 疗养院药品的形象介绍；作用说明另起一段，不再带前缀。
EN_CONTENT.update({
    '一小瓶淡金色的露，摇过以后，液面仍很平静。闻起来像晒过的枕头。': 'A small bottle of pale gold dew. Its surface stays still after shaking; it smells like a pillow dried in sunlight.',
    '蓬松的白糖团，拆开包装就缓缓鼓起，像还在呼吸。': 'A fluffy white lump of sugar. Once unwrapped, it slowly swells as if still breathing.',
    '细粒在舌尖化开，几个忘掉的颜色先后浮上来。': 'The grains dissolve on your tongue, bringing back several forgotten colours one after another.',
    '半透明的胶囊里悬着一滴浅绿液体，始终没有碰到内壁。': 'A drop of pale green liquid hangs inside a translucent capsule, never touching its walls.',
    '药锭表面布满细小圆纹，握在手里，比体温凉一点。': 'Tiny circular grooves cover the tablet. It feels a little cooler than your hand.',
    '白片一碰水就响起细碎的气泡声，水面映出的旧影跟着散开。': 'The white tablet fizzes in water. Old reflections scatter with the bubbles.',
    '硬片咬开时几乎没有味道，齿间只留下干净的粉末。': 'The hard tablet has almost no taste. Biting it leaves clean powder between your teeth.',
    '细长滴管里装着清亮的液体，每一滴都悬得很久才落下。': 'Clear liquid fills a slender dropper. Each drop hangs for a long time before falling.',
    '柔软的凝片贴着纸包，揭下来时，还拉着一根透明的细丝。': 'A soft gel sheet clings to its wrapper, trailing a transparent thread when peeled away.',
    '糖衣甜得很淡。含化以后，脑海里那阵刺痛远了一点。': 'The sugar coating is barely sweet. As it melts, the sting in your thoughts feels further away.',
    '边缘微微结晶的白片，咸味像眼泪，包装却没有水迹。': 'A white tablet with crystallised edges. It tastes like tears, though its wrapper is dry.',
    '糖心泛着温润的浅黄，咬开时有一点松软的阻力。': 'The pale yellow centre gives softly as you bite into it.',
    '小瓶里亮着晨光。拧开盖子，冷露的气味先飘出来。': 'Morning light glows inside the little bottle. Unscrew the cap, and the scent of cold dew escapes first.',
    '白片圆得像瓷器上落下的一枚小扣，表面没有刻字。': 'A round white tablet, like a small button fallen from porcelain, with no writing on its surface.',
    '薄片带着清凉的香气，压在舌下，仿佛有人拉开了窗帘。': 'A thin tablet with a cool scent. Holding it under your tongue feels like someone drawing the curtains open.',
    '纸包里有一撮细雪，捏在指间不化，贴近额头却很凉。': 'A pinch of fine snow rests in the wrapper. It does not melt between your fingers, but feels cool against your brow.',
})

# 地板作用信息按实际定义生成。
EN_CONTENT.update({
    '踩踏不会折断高丛。': 'Walking across does not break tall grass.',
    '液体扩散速度降为原来的 1/{n}。': 'Liquid spread slows to 1/{n} of its usual rate.',
    '站在其上，视野 +{n} 格。': 'Standing here extends vision by {n} cells.',
    '声响半径减少 {n} 格，至少保留 1 格。': 'Sound radius decreases by {n} cells, to a minimum of 1.',
    '植物不能在其上生长。': 'Plants cannot grow here.',
    '每次挥发额外蒸去 {n} 单位液体。': 'Each evaporation interval removes {n} additional units of liquid.',
    '每 2 回合吸去 {n} 单位液体，不产生气体。': 'Absorbs {n} units of liquid every 2 rounds without producing gas.',
    '液体每次可流出的量增至 {n} 倍。': 'Each liquid flow can carry {n} times its usual amount.',
    '气体每次消散额外减少 {n} 单位。': 'Each gas dissipation interval removes {n} additional units.',
    '每 3 回合造成清醒创伤 {n}；稳定意识不受伤。': 'Causes {n} lucidity trauma every 3 rounds; stable consciousness is unharmed.',
    '地势是本格在全层的高度（0 低洼 – 3 高处）：液体按地势差流向低处，低洼处更容易积液。': "Elevation is this cell's height within the layer (0 low, 3 high). Liquid flows downhill and tends to pool in low places.",
})

# 异象次级文风审读。
EN_CONTENT.update({
    '逆光里立着一个读者，脸看不清。它低着头，逐字读过你留下的足迹。': 'A reader stands against the light, its face hidden. Head bowed, it reads through your footprints word by word.',
    '许多张嘴挤在同一片阴影里，唱着被删去的台词。一声停下，另一声又接上。': 'Many mouths crowd into one shadow, singing deleted lines. As one voice stops, another takes its place.',
    '那里一直有个空着的位置。你移开目光，再回头看，它仍在那里。': 'There has always been an empty place there. Look away and turn back: it is still there.',
    '牧杖下挤着一群睡梦里的黑影，背脊起伏，喉间咕噜作响。': 'A flock of dark sleeping shapes crowds beneath its crook, backs rising and throats rumbling.',
    '放映机拖着一串小机器巡行，镜头转过来，票口里伸出一张皱巴巴的手。': 'A projector roams with a train of little machines. Its lens turns toward you as a crumpled hand reaches from the ticket slot.',
    '镜头始终没有停，细长的胶片拖在身后，连你的影子也录了进去。': 'The camera never stops. A long strip of film trails behind it, recording even your shadow.',
    '指尖沾着浓墨，擦过的地方只剩一块黑色。纸上没有改正的字。': 'Thick ink stains its fingers. Every place they brush becomes a black patch; no corrections remain on the paper.',
    '尺带从黑暗里抽出来，一格格贴近脚边。最远的刻度始终看不清。': 'A measuring tape draws out of the dark, its marks creeping toward your feet. The furthest graduation is never clear.',
})

# 材料和征兆中的开发术语整理。
EN_CONTENT.update({
    '细铜丝织成网，电流沿网孔嗡嗡作响；相连电线的信号能多传四格。': 'Fine copper wire forms a humming mesh; signals along connected wires travel four cells further.',
    '格栅里吹出一阵轻风。周围三乘三格的气体消散得快一倍；多处格栅不会再加快，密封板下的气仍留着。': 'A light draft comes through the grille. Gas in the surrounding three-by-three area dissipates twice as fast; extra vents do not compound this, and sealed plates still preserve gas.',
    '白瓷壁透着湿润的光。贴近它，每四回合能洗短一项征兆两回合，正负都洗；刚用过洗兆液时，也要等这段间隔。': "Damp light shines through the porcelain. Every four rounds it shortens one adjacent creature's portent by two rounds, beneficial or harmful; washing liquid shares this interval.",
    '浅绿液体缓缓流过。积到四单位时，病原体在其中每两回合受两点完整度创伤，其他意识不受伤。': 'Pale green liquid flows slowly. At four or more units, pathogens take two integrity trauma every two rounds; other consciousness is unharmed.',
    '清亮的液面托着细碎的光。积到四单位，想象力自然恢复和异象技能冷却都快四分之一；预警和施放后的恢复仍照常。': 'Clear liquid carries small flecks of light. At four or more units, natural imagination recovery and anomaly cooldowns progress 25% faster; warnings and recovery after casting stay unchanged.',
    '透明液体洗过，身上的征兆淡了一点。至少四单位才能洗短一项征兆三回合，并耗去一单位；相隔四回合才能再洗。液面每四回合还会蒸去一单位。': 'Clear liquid fades a portent. At least four units are needed to shorten one portent by three rounds, consuming one unit; washes must be four rounds apart. One unit also evaporates every four rounds.',
    '借阅证记下新的接触，四周清楚了一点：视野增加两格，持续四回合；同类视野加成只保留最高的一份。': 'The library card records a changed contact, making the surroundings clearer: vision increases by two cells for four rounds; only the strongest bonus of this kind applies.',
    '棉糖里的空气撑住呼吸，胞尘不再追加创伤；其他毒气、火焰和敌人的创伤仍会到来。': 'Air from the cotton sugar steadies your breathing, stopping extra spore trauma. Other gases, fire and enemy trauma still affect you.',
    '一种意识指标真正恢复时，药粒也替另一种未满的指标补上至多三点；补过一次就结束。': 'When one consciousness attribute actually recovers, the grains restore up to three points of another unfilled attribute, once.',
    '念头比平时流得快，想象力自然恢复变为一点二五倍；与脑脊液同用，只取较快的一份。': 'Thoughts flow faster: natural imagination recovery becomes 1.25 times normal. With cerebrospinal fluid, only the faster rate applies.',
    '凝片替你垫住下一次创伤，少受一点，随即消散。': 'The gel cushions the next actual trauma by one point, then dissolves.',
    '扇叶朝北转动，风把前方六格内的气体每回合推远一格；气体遇墙或满格就停，不同的气团也不会被搅成一种。风只搬动原有的气体。': 'The fan turns north, moving gas within six cells ahead one cell further each round. Walls and full cells stop it; distinct gases do not merge. It only moves the gas already present.',
    '扇叶朝东转动，风把前方六格内的气体每回合推远一格；气体遇墙或满格就停，不同的气团也不会被搅成一种。风只搬动原有的气体。': 'The fan turns east, moving gas within six cells ahead one cell further each round. Walls and full cells stop it; distinct gases do not merge. It only moves the gas already present.',
    '扇叶朝南转动，风把前方六格内的气体每回合推远一格；气体遇墙或满格就停，不同的气团也不会被搅成一种。风只搬动原有的气体。': 'The fan turns south, moving gas within six cells ahead one cell further each round. Walls and full cells stop it; distinct gases do not merge. It only moves the gas already present.',
    '扇叶朝西转动，风把前方六格内的气体每回合推远一格；气体遇墙或满格就停，不同的气团也不会被搅成一种。风只搬动原有的气体。': 'The fan turns west, moving gas within six cells ahead one cell further each round. Walls and full cells stop it; distinct gases do not merge. It only moves the gas already present.',
})

EN_CONTENT.update({
    '一只半透明的薄膜囊，囊口收得很紧，里面没有风。': 'A translucent membrane sac with its mouth drawn tight. There is no breeze inside.',
    '放在目标格后，四回合内从本格或相邻四格吸去至多四单位气体。使用消耗一个，可带回主梦。': 'Place it at a target cell to absorb at most four units of gas from that cell or its four neighbours over four rounds. Consumes one; usable in the Main Dream.',
    '窄玻片夹在纸套里，迎着光看，边缘泛出淡蓝。': 'A narrow glass slide rests in a paper sleeve. Its edges turn pale blue against the light.',
    '照出正常视线内两格范围的伪装，持续三回合；使用消耗一片，可带回主梦。': 'Reveals disguises within normal line of sight and two cells for three rounds. Consumes one; usable in the Main Dream.',
    # ---- 两谷位面内层间守门（2026-10-14，#83）----
    '门纹未亮——{reason}': 'The door pattern stays dark — {reason}',
    '还差 {n} 项：{items}。': 'Still {n} short: {items}.',
    '本层的手续齐了——下潜的门纹亮起来了。':
        'The paperwork here is complete — the door pattern lights up for descent.',
    '下潜手续：{have}/{total}；还差 {n} 项。': 'Descent paperwork: {have}/{total}; {n} to go.',
    '借书卡': 'library card',
    '批注': 'marginalia',
    '目录机关': 'catalog mechanism',
    '病历夹': 'patient chart',
    '叫号屏': 'queue screen',
    '一处设施': 'one facility',
    # 守门人任务提示（#85）
    '要往更深处去，得先办齐这层的手续：读一遍散落的病历夹，看一眼停摆的叫号屏，再完成任意一处设施的操作。':
        "To go deeper, finish this floor's paperwork: read the scattered patient chart, glance at the stalled queue screen, and complete any one facility's operation.",
    '要往更深处去，得先办齐这层的手续：读一张旧借书卡，读一段写满批注的桌角，再整理一座目录机关。':
        "To go deeper, finish this floor's paperwork: read an old library card, read the annotation-covered desk corner, and set one catalog mechanism in order.",
    '旧梦痕的 0 层仍是已退役的十二步教学图（教程 v{old}）：新版「梦的起始」课程不接管这一张图，旧步骤与进度不映射到新的子目标，也不按新地图伪造完成；本层地形、持有与掉落原样保留。要上新课程请开一局新梦，提示前的梦痕已备份。':
        "This save's layer 0 is still the retired twelve-step teaching map (tutorial v{old}). The new Origin course does not take over this map: old steps and progress are not mapped onto the new objectives, and nothing is credited as though the new map had been used. This layer's terrain, possessions and drops are kept exactly as they are. To take the new course, start a new dream; the dream trace was backed up before this notice.",
})

EN_CONTENT.update({
    '按 Alt+1 打开行囊。Tab 循环切换行动、行囊、构筑、自身、环境、日志；各菜单还可点击顶部文字按钮打开。':
        'Press Alt+1 for the pack. Tab cycles Act, Pack, Build, Self, Env and Log; the top buttons also open each workspace.',
    'Alt+1': 'Alt+1',
})
