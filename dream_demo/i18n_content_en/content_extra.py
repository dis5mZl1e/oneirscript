"""英文语言包 · 内容分册（由 scripts/_split_i18n_content.py 生成）。

扩展包 v2、目录 NPC、派系、跨层行程、任务日志。
键仍是中文原文；合并进 EN 的顺序见 dream_demo/i18n.py 末尾。
"""

from __future__ import annotations



# ---- 内容扩展包 v2（2026-10-11）：新洞察 13 / 新构想 10 / 新记忆碎片 12 + 效果 6 ----
EXTENSION_V2_EN = {
    # ---- 洞察名 + 描述 ----
    "磁头清洁": "Clean Tape Heads",
    "磁带墙的倒带迟滞对你无效：倒卷的吱嘎声再吵，也拖不住你的脚步。":
        "Rewind lag from tape walls no longer affects you: however loud the screech, it cannot slow your steps.",
    "弹窗拦截": "Popup Interception",
    "「失焦」对你无效：被错贴的标签在贴上之前就被你撕掉了。":
        "'Out of focus' no longer affects you: you tear off the mislabeled tag before it sticks.",
    "世纪清算": "Century Reckoning",
    "击破千禧园的异象时，额外恢复 6 点想象力——过期的系统总要有人结算。":
        "Shattering a Millennium Garden anomaly restores 6 extra imagination: someone has to settle an expired system.",
    "边界脚本": "Boundary Script",
    "在深层边界（28 层起），你的视野 +1：脚本写到这里，总要留一条看得清的路。":
        "In the Deep Boundary (floor 28+), your sight radius +1: the script leaves you a readable road this far down.",
    "绝缘体质": "Insulated Constitution",
    "电痉挛对你无效：电流认不出你这样干燥的目标。":
        "Electric spasms no longer affect you: the current cannot recognize such a dry target.",
    "不燃体质": "Non-Flammable Constitution",
    "余火不再烧灼你：燃烧征兆对你无效。":
        "Lingering fire no longer burns you: the burning portent has no hold on you.",
    "巧合收集": "Coincidence Collecting",
    "回应异常地点时获得洞察的概率显著提高（50% → 75%）。":
        "Responding to anomalous sites grants insights far more reliably (50% → 75%).",
    "思维润滑": "Well-Oiled Thinking",
    "你的所有构想冷却 -1（最低 1 回合）：念头与念头之间不再打磕绊。":
        "All your ability cooldowns -1 (min 1 round): your thoughts no longer stumble between ideas.",
    "醒梦交界": "Waking-Dream Threshold",
    "下潜一层消耗的清醒度 -1：你已经认得那条界线，不再需要用力跨。":
        "Descending one floor costs 1 less lucidity: you know that threshold by heart now.",
    "抢拍": "Snatched Beat",
    "命中正在蓄势的异象时，它的施法倒计时被拖延 1 回合：你的节拍比它的快。":
        "Hitting a winding-up anomaly delays its cast countdown by 1 round: your beat is faster than its.",
    "梦魇老主顾": "Nightmare Regular",
    "噩梦对你无效：梦魇岩、噩梦纤维与噩梦气息的心智侵蚀，被你视作家常。":
        "Nightmares no longer affect you: the mind-erosion of nightmare rock, fiber and breath feels like home cooking.",
    "稳立不摇": "Standing Firm",
    "「驻足」对你无效：句子被迫停顿的那 1 回合，你仍然走自己的路。":
        "'Rooted' no longer affects you: while sentences are forced to pause, you keep walking your own path.",
    "足音消音": "Muted Footfalls",
    "你的移动声响半径再 -1（与无声步叠加，最低仍为 1）。":
        "Your movement sound radius -1 again (stacks with Soundless Step, min 1).",
    # ---- 构想名 + 描述 ----
    "折页": "Fold",
    "把眼前折成一道窄缝：沿面朝方向挪出最多5格，墙会挡住折痕。":
        "Fold the scene into a narrow crease: slide up to 5 tiles along your facing; walls stop the fold.",
    "书签": "Bookmark",
    "在脚下夹一枚书签；再次展开时回到这里，只认同一层的页码。落点被占据时书签留下。":
        "Tuck a bookmark underfoot; unfold it again to return here — same floor's page number only. If the spot is taken, the bookmark stays behind.",
    "墨线": "Ink Line",
    "向前划一道墨：8格内沿线异象的眼睛被蒙住2回合，墨线不过墙。":
        "Draw a line of ink ahead: anomalies along it within 8 tiles are blinded for 2 rounds; the ink does not cross walls.",
    "删划": "Strike-Through",
    "划去面前一处薄弱障碍：硬度不超过2，边界、机关、柜箱和任务设施不能删去。":
        "Strike out one frail obstacle before you: hardness 2 or less. Boundaries, mechanisms, cabinets and task fixtures cannot be deleted.",
    "夹页": "Pressed Between Pages",
    "把最近的异象夹在页间：5格内一个可见敌对异象2回合不能移动，仍可出手。":
        "Press the nearest anomaly between the pages: one visible hostile anomaly within 5 tiles cannot move for 2 rounds, though it may still strike.",
    "旁注": "Marginalia",
    "在空白处补几笔：显影周围8格的地形，不替你看见暗处的人和物。":
        "Scribble in the margins: reveal the terrain within 8 tiles — it will not show you what hides there.",
    "急冻链": "Frost Chain",
    "霜顺着视线蔓延：视野内最近的 5 个失控意识被冻结 2 回合。":
        "Frost spreads along your sight: the 5 nearest visible uncontrolled minds are frozen for 2 rounds.",
    "静电弧": "Static Arc",
    "指尖蹦出一记短促的电弧：命中近旁 3 格内的一个失控意识，造成 3 点创伤并使其迟缓 2 回合。":
        "A brief arc snaps from your fingertip: hits one uncontrolled mind within 3 tiles for 3 damage and slows it for 2 rounds.",
    "涂鸦": "Doodle",
    "把目标格周围半径 2 的地板涂成易燃的书页地：为纵火的念头铺一张纸。":
        "Paint floor tiles within radius 2 of the target into flammable page-ground: lay sheets of paper for your arsonist thoughts.",
    "闪现": "Blink",
    "在视线内瞬移到 8 格以内的空地：梦没来得及拦你。":
        "Blink to an empty tile within 8 squares in your sight: the dream fails to stop you.",
    "遗忘喷剂": "Forget-Spray",
    "喷出一团蛾粉，视野内所有失控意识都忘记你在哪（警觉重置）。":
        "Spray a cloud of moth dust: every uncontrolled mind in sight forgets where you are (alerts reset).",
    "深呼吸": "Deep Breath",
    "在梦里做一次真正的深呼吸：回复 6 点清醒度。":
        "Take one real deep breath inside the dream: restore 6 lucidity.",
    "安神香": "Calming Incense",
    "点起一支不存在的香：清除你身上全部负面征兆，并镇静 3 回合。":
        "Light an incense that does not exist: clears all your negative portents and calms you for 3 rounds.",
    "净化风": "Cleansing Wind",
    "想象一阵穿过梦境的风：视野内所有气体被一扫而空。":
        "Imagine a wind crossing the dream: every gas in sight is swept away.",
    "像素拆解": "Pixel Dismantling",
    "把视野内一面千禧园的装饰墙拆成色块，回收 8 点想象力（结构墙除外）。":
        "Dismantle one decorative Millennium Garden wall in sight into color blocks, recovering 8 imagination (structural walls excluded).",
    "静默协议": "Silence Protocol",
    "给自己挂上静音滤镜：8 回合内你的声音半径被压到最低。":
        "Hang a mute filter on yourself: your sound radius is pressed to the minimum for 8 rounds.",
    # ---- 新记忆碎片（名 + 描述）----
    "随身听的旧歌单": "The Old Playlist on the Walkman",
    "一张写满歌名的清单，每一首都还停在播放键按下之前。":
        "A list of song titles, every one still frozen before the play button was pressed.",
    "磁带的底噪": "Tape Hiss",
    "倒带时的沙沙声里，有一段属于你的安静。":
        "Inside the rewinding hiss, there is a patch of quiet that belongs to you.",
    "忙音的下午": "An Afternoon of Dial Tones",
    "电话那头没人接，你却记得整个下午的心跳。":
        "No one picked up on the other end, yet you remember that whole afternoon's heartbeat.",
    "像素宠物的墓碑": "The Pixel Pet's Gravestone",
    "屏幕暗下去的时候，它还保持着奔跑的姿势。":
        "When the screen went dark, it was still mid-run.",
    "气泡膜的解压": "Bubble Wrap Relief",
    "每一个气泡破掉的声音都恰到好处。":
        "Every pop lands exactly right.",
    "门铃的半声": "Half a Doorbell Chime",
    "按了一半就缩回的手，和永远没说完的拜访。":
        "A hand that pulled back mid-press, and a visit never finished saying hello.",
    "草叶的松脱": "Slipping the Grass Blade",
    "从草丛里挣脱出来的那个下午，腿上还留着草的划痕。":
        "That afternoon you tore free of the grass, its scratches still on your legs.",
    "空药瓶的回甘": "The Aftertaste of an Empty Vial",
    "苦过之后，舌根泛起的一点甜特别诚实。":
        "After the bitterness, the hint of sweet on your tongue is unusually honest.",
    "三十层的电梯按钮": "The 30th-Floor Elevator Button",
    "最高那一层的按钮亮过一次，之后再没亮过。":
        "The top floor's button lit up once, and never again.",
    "执笔者的一滴墨": "A Drop of the Author's Ink",
    "它替你写结尾时，一滴墨落在稿纸边缘——像一颗不肯熄灭的星。":
        "While writing your ending, one drop of ink fell by the page's edge — like a star refusing to go out.",
    "回响戒指的颤动": "The Echo Ring's Tremble",
    "戒指还记得每一声撞在门上的回音。":
        "The ring remembers every echo it struck off a door.",
    "电路板的嗡鸣": "The Circuit Board's Hum",
    "通电的那一瞬间，整个玩具都在小声唱歌。":
        "The instant current flowed, the whole toy began to hum a little song.",
    # ---- 新记忆效果（效果名 / 一句效果 / 详情）----
    "毒雾的失敏": "Poison-Fog Desensitized",
    "免疫毒气": "Immune: poison",
    "毒气的心智侵蚀对你无效——你早就尝过更怪的味道。":
        "Poison's mind-erosion has no hold on you — you have tasted far stranger.",
    "倒带的静音": "Rewind Muted",
    "免疫倒带迟滞": "Immune: rewind lag",
    "磁带墙的倒卷声拖不住你的脚步。": "The screech of rewinding tape cannot slow your steps.",
    "门风的驯服": "Door-Wind Tamed",
    "免疫门扉眩晕": "Immune: door vertigo",
    "门隙之风让你看什么都稳稳当当。": "The wind through door gaps leaves your vision rock-steady.",
    "草叶的松动": "Loosened Grass",
    "免疫缠住": "Immune: snared",
    "捕梦草卷不住你的脚踝——你记得怎么从草叶里脱身。":
        "Dream-catching grass cannot bind your ankles — you remember how to slip free.",
    "满格的存档": "A Full Save File",
    "想象上限 +10": "Max imagination +10",
    "想象力上限 +10，获得时立即回填 10 点想象力。":
        "Max imagination +10, immediately refills 10 imagination when gained.",
    "醒着的顶层": "Awake at the Top Floor",
    "清醒上限 +8": "Max lucidity +8",
    "清醒度上限 +8，获得时立即回填 8 点清醒度。":
        "Max lucidity +8, immediately refills 8 lucidity when gained.",
    # ---- §13 新增战斗构想：名称、说明、瞄准与结算消息 ----
    "截拍": "Beat Cut",
    "借位": "Cross Step",
    "横切": "Arc Slash",
    "折光矢": "Refracted Bolt",
    "穿念针": "Piercing Needle",
    "迟响弹": "Delayed Shell",
    "钉影枪": "Shadow Pin",
    "牵引钩": "Tow Hook",
    "雷珠": "Arc Orb",
    "裂地环": "Fault Ring",
    "纸刃旋流": "Paper Blade Cyclone",
    "逆风幕": "Backdraft Screen",
    "对相邻的一个异象执行一次当前近战；若它正在蓄势，打断这次蓄势并令其停顿 1 回合。没有可打断动作时仍可当作普通近战挥出。":
        "Make one current melee attack against an adjacent anomaly; if it is winding up, interrupt that windup and leave it recovering for 1 round. If there is nothing to interrupt, it still swings as a normal melee attack.",
    "对相邻的一个异象执行一次当前近战，随后落进一个同时贴近原站位与目标的合法空格，最多移动 1 格。没有合法落点时不能出手。":
        "Make one current melee attack against an adjacent anomaly, then land in a legal space adjacent to both your old position and the target, moving at most 1 cell. You cannot use it without a legal landing.",
    "扫过面朝方向与两侧相邻的三格；每个异象只承受一次当前近战基础伤害的 70%（向上取整，至少 1）。":
        "Sweep the three cells in your facing direction and both sides; each anomaly takes 70% of your current melee base damage once (rounded up, at least 1).",
    "射出一支真实弹体，路径总长 12：命中首个实体造成 3 点创伤；可在普通墙面几何折返一次，也遵循构想镜面的反射，整条路径最多反射两次。返程会伤到自己。":
        "Fire a real projectile with a total path of 12: the first entity hit takes 3 damage; it may bounce geometrically off one plain wall and also follows construct-mirror reflection rules, with at most two reflections overall. The return path can hurt you.",
    "射出一根细针，路径总长 12：最多穿过 3 个实体，创伤依次为 3／2／1；可穿透硬度×厚度合计不超过 4 的普通薄墙并削去 20 完整度，任务、边界与抗弹墙仍会挡下。":
        "Fire a needle with a total path of 12: it passes through up to 3 bodies for 3/2/1 damage; it can pierce plain thin walls whose hardness times thickness totals at most 4, removing 20 integrity, while task, boundary and bullet-resistant walls still stop it.",
    "朝视野内最远 10 格的落点投出一枚虚构弹体；落地留下可见倒计时弹，离手后 2 个真实回合引爆（半径 2、威力 3，敌我共担）。同层最多保留 2 枚未爆弹。":
        "Throw a fictional shell at a visible landing up to 10 cells away; it leaves a visible countdown shell that detonates after 2 real rounds (radius 2, power 3, harming friend and foe). At most 2 unexploded shells per layer.",
    "朝最远 10 格射出钉影：首个实体受 2 点创伤；若沿实际入射方向其后一格是合法实墙，则驻足 3 回合，否则迟缓 2 回合。":
        "Fire a shadow pin up to 10 cells: the first entity takes 2 damage; if the cell directly behind it along the actual incoming direction is a legal solid wall, it is rooted for 3 rounds, otherwise slowed for 2.",
    "朝最远 8 格抛出钩索：命中可移动的敌对异象时，沿实际飞行路径把它逆向拉近最多 3 格，停在玩家相邻格之前；无直接伤害。没有目标也可合法释放。":
        "Throw a tow hook up to 8 cells: on hitting a movable hostile anomaly, pull it up to 3 cells back along the actual flight path, stopping before a cell adjacent to you; no direct damage. It can be released legally with no target.",
    "把雷珠投到最远 8 格：实际落点生成 16 点水、四邻各 6 点（最多 40 点），随后对相连的导电介质充能，沿用真实电场规则；没有额外爆炸伤害。":
        "Throw an arc orb up to 8 cells: the actual landing creates 16 water and 6 in each orthogonal neighbor (up to 40), then charges connected conductive medium using the real electric-field rules; no extra explosion damage.",
    "以自身为中心，作用切比雪夫距离恰好为 3 的外环：合法墙体完整度 −25，开放地面降低一档，环上生物受 2 点创伤并被径向推开 1 格；中心不受这次冲击。":
        "Centered on you, affect the outer ring at exactly Chebyshev distance 3: legal walls lose 25 integrity, open ground drops one elevation step, and creatures on the ring take 2 damage and are pushed 1 cell radially outward; the center is untouched by this impact.",
    "在施放位置立起半径 2 的固定刃环，持续 4 回合：每个真实回合结束时环上生物受 2 点创伤，同实例每回合最多一次；自己也一样，重施会替换旧刃环。":
        "Raise a fixed radius-2 blade ring at the casting position for 4 rounds: at the end of each real round, creatures on the ring take 2 damage, at most once per instance per round; you are hurt too (1 damage), and recasting replaces the old ring.",
    "从面朝格起立起长 6、宽 5 的风幕，持续 4 回合：气体每回合沿远离玩家的方向移动一格；首个穿过风幕的真实弹体剩余射程 −2，投掷体按实际提前落地。自身弹体同样受影响。":
        "Raise a screen 6 long and 5 wide starting at the facing cell for 4 rounds: gas moves one cell away from you each round; the first real projectile crossing the screen loses 2 remaining range, and thrown bodies land early. Your own projectiles are affected too.",
    "构想瞄准：{name} · 射程 {range} · 费用 {cost} · Esc 取消不消耗。":
        "Construct aim: {name} · range {range} · cost {cost} · Esc cancels without spending.",
    "借位落点 ({x}, {y})": "Cross Step landing ({x}, {y})",
    "近战构想只能选择相邻的目标。":
        "A melee construct can only target an adjacent creature.",
    "先选择一个相邻的异象。": "Choose an adjacent anomaly first.",
    "附近没有可供借位的合法空格。":
        "There is no legal space nearby to cross-step into.",
    "这个构想现在无法瞄准。": "This construct cannot be aimed right now.",
    "截拍打断了它的蓄势。": "Beat Cut interrupts its windup.",
    "截拍挥出——目标没有可打断的动作。":
        "Beat Cut swings — the target has no windup to interrupt.",
    "横切扫过 {n} 个目标。": "Arc Slash sweeps {n} targets.",
    "横切掠过三格——没有碰到目标。":
        "Arc Slash sweeps three cells — no target touched.",
    "借位：一击之后落到了侧后的空格。":
        "Cross Step: after the blow you land in a flanking space.",
    "借位挥出——没有可供侧移的落点。":
        "Cross Step swings — no space available to shift into.",
    "你对相邻的目标挥出一次近战。":
        "You strike an adjacent target with a melee attack.",
    "近战构想挥空了。": "The melee construct swings at empty air.",
    "选择一个相邻的目标。": "Choose an adjacent target.",
    "那里没有可以攻击的目标。": "There is no attackable target there.",
    "稳定意识不在这次构想的对象里。":
        "Stable minds are not valid targets for this construct.",
    "斜角被两堵墙夹住了。": "The diagonal is pinched shut by two walls.",
    "预选的借位落点已经失效。":
        "The preselected Cross Step landing is no longer valid.",
    "那个目标超出了射程。": "That target is out of range.",
    "那里看不见，无法锁定。": "You cannot see there, so you cannot lock on.",
    "折返的光矢擦到了自己。": "The returning bolt grazes you.",
    "光矢命中了目标。": "The bolt hits its target.",
    "光矢撞在墙上折落。": "The bolt breaks against a wall.",
    "光矢飞出射程后消散。": "The bolt fades once it flies out of range.",
    "穿念针穿过了 {n} 个实体。": "Piercing Needle passes through {n} bodies.",
    "细针钉在了墙上。": "The needle pins itself into a wall.",
    "细针飞出射程后消散。": "The needle fades once it flies out of range.",
    "钉影把它钉在了墙上。": "Shadow Pin nails it to the wall.",
    "钉影命中了目标，拖慢了它的脚步。":
        "Shadow Pin hits the target and slows its steps.",
    "钉影枪钉进了墙里。": "Shadow Pin buries itself in the wall.",
    "钉影枪的空响散在梦里。": "Shadow Pin's empty report scatters into the dream.",
    "钩索收回来时什么都没抓住。": "The tow hook returns with nothing caught.",
    "钩索把它拉近了 {n} 格。": "The tow hook pulls it {n} cells closer.",
    "钩索挂住了它，却拉不动。": "The tow hook catches it but cannot pull it.",
    "迟响弹落在 ({x}, {y})，倒计时开始。":
        "The delayed shell lands at ({x}, {y}); the countdown begins.",
    "雷珠在 ({x}, {y}) 化成一摊导电的水（{n} 点）。":
        "The arc orb dissolves into conductive water at ({x}, {y}) ({n} points).",
    "投掷路径被墙挡住了。": "The throwing path is blocked by a wall.",
    "同层最多保留 2 枚未爆弹——先等旧弹炸开。":
        "At most 2 unexploded shells per layer — wait for the old one to detonate.",
    "逆风幕削弱了这次投掷（最远 {n} 格）。":
        "The backdraft screen weakens this throw (max {n} cells).",
    "面朝方向没有可以立起风幕的空间。":
        "There is no room to raise a backdraft screen in the facing direction.",
    "纸刃围成一圈，在梦里转了四回合。":
        "Paper blades ring around you and spin for four rounds.",
    "逆风幕立了起来：气流开始背离你。":
        "The backdraft screen rises: the air begins to flow away from you.",
    "裂地环塌了一圈：{walls} 面墙开裂，{ground} 格地势下沉，{hurt} 个目标受创。":
        "The fault ring collapses: {walls} walls crack, {ground} cells sink, {hurt} targets are hurt.",
    "迟响弹的倒计时归零。": "The delayed shell's countdown reaches zero.",
    # ---- 面板与教学文案的补齐（动态键，AST 扫不到时由此兜底） ----
    "消耗 1 件工具": "Consume 1 tool",
    "耗时 1 回合": "Takes 1 round",
    "距离": "Distance",
    "射程": "Range",
    "F 区两份有限液体样本已备好。":
        "Two limited liquid samples are ready in Sector F.",
    "练习位置被占用，请先让开。":
        "The practice spot is occupied — step aside first.",
    "这份练习教材已经借出。":
        "This practice material is already on loan.",
    "被动教材仅本层生效；请查看来源，并用诱饵验证回响。":
        "Passive teaching material only works on this layer; check its source and verify the echo with bait.",
}
# 合并入口在 core 侧（dream_demo/i18n.py）：EXTENSION_V2_EN / EXTENSION_V2_MESSAGES_EN
# 与其它 EN_* 分表一样由 i18n.py 尾部统一 EN.update()。

# ---- 构想 v2 结算消息 ----
EXTENSION_V2_MESSAGES_EN = {
    "霜顺着视线蔓延：冻结了 {n} 个失控意识（2 回合）。":
        "Frost crawls along your sight: froze {n} uncontrolled minds (2 rounds).",
    "静电弧在指尖蹦了一下——近旁 3 格内没有可以击中的失控意识。":
        "The static arc snaps at your fingertip — no uncontrolled mind within 3 tiles to strike.",
    "静电弧咬住了 {enemy}：3 点创伤，它的动作迟了下来。":
        "The static arc bites {enemy}: 3 damage, and its movements slow down.",
    "纸上才能涂写——那片没有可以改的地板。":
        "Only paper can be doodled on — no paintable floor there.",
    "你把 {n} 格地板涂成了易燃的书页地。": "You paint {n} floor tiles into flammable page-ground.",
    "闪现构想散了——视线之内没有可以立足的空地。":
        "The blink dissolves — no empty tile within sight to land on.",
    "梦没来得及拦你——你已站在 ({x}, {y})。": "The dream fails to stop you — you are already at ({x}, {y}).",
    "蛾粉散开——{n} 个失控意识忘了你在哪。":
        "Moth dust scatters — {n} uncontrolled minds forget where you are.",
    "蛾粉落了个空——视野内没有可以遗忘你的东西。":
        "The moth dust falls on nothing — nothing in sight could forget you.",
    "你在梦里做了一次真正的深呼吸（清醒 +{n}）。":
        "You take one real deep breath inside the dream (lucidity +{n}).",
    "安神香燃起来：{n} 个负面征兆散了，镇静托住你的念头（3 回合）。":
        "The calming incense burns: {n} negative portents disperse, and calm holds your thoughts (3 rounds).",
    "一阵风穿过梦境：{n} 格的气体被一扫而空。":
        "A wind crosses the dream: {n} tiles of gas are swept away.",
    "视野里没有可以拆成色块的千禧园墙。": "No Millennium Garden wall in sight to dismantle into color blocks.",
    "{kind}哗啦一声拆成色块（想象力 +8）。": "The {kind} crashes apart into color blocks (imagination +8).",
    "静默协议上线：{turns} 回合内你的声音半径被压到最低。":
        "Silence protocol online: your sound radius is pressed to the minimum for {turns} rounds.",
    "世纪清算：过期的系统被你结清了（想象力 +{n}）。":
        "Century reckoning: the expired system is settled (imagination +{n}).",
    "你抢在它的节拍前面——「{skill}」的蓄势被拖慢了 1 回合。":
        "You snatch the beat before it does — the wind-up of '{skill}' is delayed by 1 round.",
}

# ---- 图鉴「梦中人」分类（2026-10-11）：分类名 + NPC 属性行 + 交互记录 ----
CATALOG_NPC_EN = {
    "梦中人": "Dream Folk",
    "关系": "Bond",
    "创伤": "Trauma",
    "与其交谈过。": "Spoke with them.",
}

# ---- 派系与声望（§4.2/§4.3，2026-10-11）----
FACTIONS_EN = {
    "拾荒协会": "Salvagers' Guild",
    "安全回收、清理威胁、保全可用物。":
        "Safe recovery, clearing threats, preserving usable things.",
    "可选择的委托、标记猎场、回收服务、附近巡卫协助。":
        "Optional commissions, marked hunting grounds, recovery services, nearby escort aid.",
    "守忆会": "Memory Keepers",
    "记录、辨认、保留不可替代的记忆。":
        "Recording, identifying, preserving irreplaceable memories.",
    "未知地点情报、设施鉴定、显影服务、重要故事线。":
        "Unknown-place intelligence, facility appraisal, developing services, major storylines.",
    "梦路同盟": "Dream Paths Alliance",
    "路线、庇护、互助与重逢。": "Routes, shelter, mutual aid and reunions.",
    "中继点、渡口、旅人消息、临时庇护和迁移地点。":
        "Relay points, ferries, traveler news, temporary shelter and relocation sites.",
    "失信": "Disgraced",
    "拒绝高风险委托与非必要支援，关键安全出口仍可用。":
        "Refuses high-risk commissions and optional support; critical safe exits stay open.",
    "戒备": "Wary",
    "服务条件更严格，先进行说明或补偿。":
        "Services come with stricter terms; explain or compensate first.",
    "陌生": "Unfamiliar",
    "正常服务和基础委托。": "Normal services and basic commissions.",
    "可信": "Trusted",
    "增加一条情报、服务选择或一次当地支援。":
        "One extra lead, service option, or one local assist.",
    "托付": "Entrusted",
    "开放少数重要委托、特殊设施权限；不增加普遍战斗倍率。":
        "Opens a few major commissions and facility rights; no blanket combat multiplier.",
    "{faction}的账本上添了一笔（{reason}）：{old}（{old_tier}）→ {new}（{new_tier}）。":
        "{faction} adds a line to their ledger ({reason}): {old} ({old_tier}) → {new} ({new_tier}).",
    "{faction}的账本上添了一笔（{reason}）：{old} → {new}（{tier}）。":
        "{faction} adds a line to their ledger ({reason}): {old} → {new} ({tier}).",
    "完成委托「{quest}」": "completed the commission '{quest}'",
}

# 跨层行程（§6.3）：world/travel.py 的去向播报。
TRAVEL_EN = {
    "「{name}」动身去了别处——你说不准会在哪层再碰上。":
        "\"{name}\" set off for somewhere else — no telling on which layer you will meet again.",
}

# 任务日志面板（§14）：ui/task_journal.py。
JOURNAL_EN = {
    "第 {n} 层": "layer {n}",
    "委托人就在本层——随时可交付。":
        "The giver is on this layer — deliver any time.",
    "委托人在本层。": "The giver is on this layer.",
    "委托人在{place}——回去找 TA 才能交付。":
        "The giver is on {place} — go back to deliver.",
    "任务日志": "Task Journal",
    "没有接下的委托。": "No commissions taken.",
    "委托从对话里接——能给活的梦中人会把选项摆在明面上。":
        "Commissions are taken in conversation — dream folk who have work will put it on the table.",
    "地点": "Place",
    "委托人": "Giver",
    "报酬": "Reward",
}
