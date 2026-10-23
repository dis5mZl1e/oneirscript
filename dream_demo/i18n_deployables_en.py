"""英文语言包 · A2 新增十件（2026-10-22）。

键仍是中文原文；合并进 EN 的顺序见 dream_demo/i18n.py 末尾。

覆盖三类文本：物品名与描述、图鉴「作用」行与「作用说明」行、以及十件
在运行期吐出的提示（装置登记、回合结算、瞄准提示）。
"""

from __future__ import annotations

EN_DEPLOYABLES = {
    # ---- 物品名 ----
    "误点的夜班灯": "The Mis-clocked Night Lamp",
    "折叠虹吸管": "Folded Siphon Tube",
    "应急蜡封": "Emergency Wax Seal",
    "冬天的样本": "A Sample of Winter",
    "拆迁用的线轴": "Demolition Spool",
    "折好的逃生通道": "Folded Escape Route",
    "未寄出的雷暴": "The Unsent Storm",
    "最后一圈安静": "The Last Circle of Quiet",
    "留给醒来的那一口": "A Breath Kept for Waking",
    "瓶装天亮": "Bottled Sunrise",

    # ---- 物品描述 ----
    "值班表上写错了班次。灯芯一直亮着，每隔几个回合就咳一声——那声音够远，"
    "够让别的东西循着过来。":
        "The shift on the roster was written wrong. The wick keeps burning, and every "
        "few rounds it coughs once—loud enough and far enough to draw something else along.",
    "两截软管折在一起。展开后架在源与出口之间，它每回合替你搬一点东西，"
    "直到管子灌满或者源被抽干。":
        "Two lengths of soft hose, folded together. Unfold it across a source and an "
        "outlet and it carries a little each round, until the tube is full or the source runs dry.",
    "一小管备用蜡。挤在门口的地上会堆成一堵墙，挡住不该进来的东西——但蜡会化，"
    "热得越快化得越快。":
        "A small tube of spare wax. Squeezed onto the floor at a doorway it piles into a "
        "wall that keeps out what should not come in—but wax melts, and the hotter it gets "
        "the faster it goes.",
    "装着液氮的薄壁瓶。摔碎时白雾漫开：中心冻得最实，四周只是发凉；地板不会被整层冻住。":
        "A thin-walled bottle of liquid nitrogen. When it shatters the white fog spreads: the "
        "centre freezes hardest, the edges are only cold, and the floor never freezes over whole.",
    "一卷绷紧的细线。抽出去能割开挡路的东西——一次只割三处，每回合割一点。":
        "A spool of wire pulled taut. Feed it out and it cuts through whatever blocks the "
        "way—three places at a time, a little each round.",
    "两条折好的路，接在两个看得见的空位之间。走过去比绕远路近，但只够走三趟。":
        "Two folded paths, joined between two empty places you can see. Walking it is shorter "
        "than going around, but it holds for only three crossings.",
    "一封没寄出去的雷暴信。落地之后它分四回合把攒下的电倒出来：导电的记忆液和带静电的尘。":
        "A thunderstorm letter never sent. Once it lands it pours out its stored charge over "
        "four rounds: conductive memory-liquid and charged dust.",
    "一圈薄薄的静音。声音穿过它时会再哑一分——只挡声音，不挡眼睛。":
        "A thin circle of silence. Sound crossing it goes hoarse again—it blocks sound only, "
        "never sight.",
    "最后一口气，攒着等天亮。喝下去清醒 30、心智 20，还洗得掉一件黏在身上的东西。":
        "A last breath, saved for morning. Drinking it gives 30 lucidity and 20 mind, and "
        "washes one thing stuck to you off.",
    "瓶里封着一小段早晨。摔开先亮两回合引信，然后三回合里把八十单位燃油倒出来点着。":
        "A small piece of morning sealed in a bottle. Break it and the fuse burns for two "
        "rounds, then three rounds of eighty units of fuel spill out and catch.",

    # ---- 图鉴「作用」行 ----
    "夜灯：定时发声": "Night lamp: timed sound",
    "虹吸：定点搬料": "Siphon: move material",
    "蜡封：临时隔断": "Wax seal: temporary barrier",
    "液氮：低温冻结": "Liquid nitrogen: cryogenic freeze",
    "线轴：定向破障": "Spool: directional breaching",
    "折路：定点往返": "Folded route: fixed-point transit",
    "蓄电：延时放电": "Charge store: delayed discharge",
    "静音圈：削弱声响": "Quiet ring: dampen sound",
    "储备：清醒与洗涤": "Reserve: lucidity and cleansing",
    "瓶装天亮：延时纵火": "Bottled sunrise: delayed arson",

    # ---- 图鉴「作用说明」行 ----
    "选 6 格内一处可见空地放下：灯芯照出半径 3 的弱光，落地即发声一次（声径 12），"
    "第 3／6／9 回合各再咳一次；灯会被火烧掉，光随之熄灭。":
        "Set it on a visible empty cell within 6: the wick lights a radius-3 glow, coughs once "
        "on landing (sound radius 12), and coughs again on rounds 3, 6 and 9. Fire burns it "
        "out and the light goes with it.",
    "选两处可见格（源与出口，相距不超过 6 格），源须有液体或气体：液体每回合搬 8 单位、"
    "合计 64；气体每回合 4 单位、合计 32。出口装满或源被抽干即停转（不吞材料）；8 回合后撤下。":
        "Pick two visible cells (source and outlet, no more than 6 apart); the source must hold "
        "liquid or gas. Liquid moves 8 units a turn, 64 in all; gas moves 4 a turn, 32 in all. "
        "It stops when the outlet fills or the source empties, and never swallows the material. "
        "Removed after 8 rounds.",
    "选 4 格内一处可见空地：挤出的 20 单位熔蜡堆成一堵完整度 60 的蜡墙，可挡住去路"
    "（唯一必经路不让封）。10 回合后逐步化回等量熔蜡；附近起火会提前融化。":
        "Squeeze it onto a visible empty cell within 4: 20 units of molten wax pile into a wall "
        "of 60 integrity that blocks the way—a cell that would seal the only route is refused. "
        "After 10 rounds it melts back into the same amount of wax; fire nearby melts it early.",
    "掷出摔碎：落点放出 24 单位液氮（中心 8、四邻各 4），按既有冻结／凝结规则转化，"
    "地板不会被整层冻住；装不下的留在容器里。":
        "Thrown and shattered: the landing cell releases 24 units of liquid nitrogen (8 at the "
        "centre, 4 to each side) and converts by the usual freezing and condensing rules. The "
        "floor never freezes over whole, and what does not fit stays in the container.",
    "选一个方向：沿线 6 格内至多 3 处非保护障碍被细线咬住，每回合合计侵蚀 60 点完整度"
    "（合计 180），按距近到远分配；线抽完即松。":
        "Pick a direction: up to 3 unprotected obstacles within 6 cells are caught by the wire, "
        "which eats 60 integrity a turn in total (180 overall), nearest first. When the wire runs "
        "out it goes slack.",
    "选两处可见空位（相距不超过 8 格）铺开：踩到一端就被送到另一端，最多 3 趟，"
    "每趟花一次正常移动；不跨层、不跳任务门、边界与禁行格一律不送。":
        "Lay it between two visible empty cells (no more than 8 apart): stepping on one end "
        "sends you to the other, up to 3 crossings, each costing a normal move. It never crosses "
        "floors, skips quest gates, or lands on borders and no-go cells.",
    "掷出后分 4 回合倒出电荷（每回合 15 单位导电液态记忆、10 单位静电尘），最后放一次电："
    "沿真实连通介质传播，同一回合每个目标只挨一次；介质不导电就散掉。":
        "After it lands it pours out its charge over 4 rounds (15 units of conductive "
        "memory-liquid and 10 of charged dust a turn), then discharges once: it travels through "
        "genuinely connected material, and each target takes it only once per round. Insulating "
        "ground lets it dissipate.",
    "在脚下铺开半径 4 的静音圈，持续 6 回合：穿过边界的声响在既有传播损耗之外再衰减 6"
    "（每格最多计一次）；不清警戒，也不挡非声音的感知。":
        "Spread it at your feet as a radius-4 quiet zone for 6 rounds: sound crossing the border "
        "loses 6 more than its usual travel loss, counted once per cell. It does not clear "
        "alertness and does not block senses other than hearing.",
    "喝下后清醒 +30、心智 +20，并洗掉一项可清洗的负面附着、把一项可清洗的负面征兆缩短至多 4 回合；"
    "正面征兆、混乱、债务与冷却都不动。":
        "Drinking it gives +30 lucidity and +20 mind, washes off one washable negative attachment, "
        "and shortens one washable negative portent by up to 4 rounds. Beneficial portents, "
        "confusion, debts and cooldowns are untouched.",
    "掷出后留 2 回合可见引信，之后 3 回合向视线可达、半径 3 的范围分批放出合计 80 单位燃油"
    "并点燃；火与爆炸都走既有燃烧规则。":
        "Thrown, it leaves a visible fuse for 2 rounds, then spreads 80 units of fuel over 3 "
        "rounds across the radius-3 cells it can see and lights them. Fire and blasts follow the "
        "usual burning rules.",

    # ---- 珍品机会来源标签 ----
    "拆迁珍品机会": "Breach treasure opportunity",
    "雷暴珍品机会": "Storm treasure opportunity",
    "天亮珍品机会": "Dawn treasure opportunity",

    # ---- 珍品机会：三个深度带各一处高成本场合 ----
    "拆到一半的工事": "Half-Dismantled Works",
    "脚手架还立着，墙上有三道旧切口——有人试过把它拆开。":
        "The scaffolding is still standing and there are three old cuts in the wall—someone tried "
        "to take it apart.",
    "脚手架上的线还绷着，切口是新的。":
        "The wire on the scaffolding is still taut, and the cuts are fresh.",
    "工具箱没上锁：里面只够带走一样。":
        "The toolbox is unlocked: there is only room to carry one thing out of it.",
    "压在旧气压计下的信": "A Letter Under the Old Barometer",
    "一封没有寄出的信压在气压计底下，纸角已经发潮。":
        "An unsent letter lies under the barometer, its corners already damp.",
    "气压计的指针在抖，信封上写着「暂勿投递」。":
        "The barometer needle is trembling; the envelope reads 'do not deliver yet'.",
    "信里的东西还没散出来，但封口已经在渗。":
        "What is inside the letter has not spilled out yet, but the seal is already leaking.",
    "留着天亮的抽屉": "The Drawer That Kept the Sunrise",
    "抽屉没关严，缝里漏出一线不刺眼的光。":
        "The drawer is not quite closed; a thread of painless light leaks out of the gap.",
    "抽屉深处有一只还没开封的瓶子，瓶壁是温的。":
        "Deep in the drawer sits an unopened bottle, and its wall is warm.",
    "里面的东西只够拿一样；拿了，另一样就留在原处。":
        "There is only enough inside for one thing; take it, and the other stays where it lies.",
    "取走{item}": "Take the {item}",

    # ---- 部署动作与拒绝提示 ----
    "举起{item}——点选落点或按方向键（Esc 取消，不消耗）。":
        "Raise {item}—pick a landing cell or use the direction keys (Esc cancels, nothing is spent).",
    "{item}不能这样放。": "{item} cannot be placed that way.",
    "那个落点放不下。": "Nothing can be set down there.",
    "{item}没有方向可指。": "{item} has no direction to point.",
    "方向无效。": "That direction is not valid.",
    "这两个落点凑不成一对。": "Those two cells do not make a pair.",
    "{item}不需要选点。": "{item} needs no target.",
    "举起{item}——{hint}（取消不消耗）。":
        "Raise {item}—{hint} (cancelling spends nothing).",
    "点选落点 · Enter 确认 · Esc 取消": "Pick a cell · Enter to confirm · Esc to cancel",
    "先选第一个落点 · 再选第二个 · Esc 取消":
        "Pick the first cell · then the second · Esc to cancel",
    "方向键选方向 · Enter 确认 · Esc 取消":
        "Direction keys choose the facing · Enter to confirm · Esc to cancel",
    "这里不能作为第一个落点——本次不消耗。":
        "This cell cannot be the first one—nothing was spent.",
    "第一个落点 ({x}, {y}) 已选：再选第二个。":
        "First cell ({x}, {y}) chosen: now pick the second one.",
    "这两个落点凑不成一对——本次不消耗。":
        "Those two cells do not make a pair—nothing was spent.",
    "这个落点不成立——本次不消耗。": "That cell does not hold—nothing was spent.",
    "部署 {name}": "Deploy {name}",
    "消耗物品 1 件": "Consumes 1 item",
    "方向键转向 · Enter 确认 · Esc 取消（不消耗）":
        "Direction keys turn · Enter to confirm · Esc to cancel (nothing spent)",
    "方向键移落点 · Enter 选定第一个 · Esc 取消（不消耗）":
        "Direction keys move the cell · Enter to take the first one · Esc to cancel (nothing spent)",
    "方向键移落点 · Enter 确认这一对 · Esc 取消（不消耗）":
        "Direction keys move the cell · Enter to confirm the pair · Esc to cancel (nothing spent)",
    "方向键移落点 · Enter 确认 · Esc 取消（不消耗）":
        "Direction keys move the cell · Enter to confirm · Esc to cancel (nothing spent)",

    # ---- 装置运行期提示 ----
    "那里立着东西，灯放不上去。": "Something is already standing there; the lamp will not fit.",
    "夜班灯亮着，咳了一声——那声音够远。":
        "The night lamp lights up and coughs once—far enough to be heard.",
    "夜班灯落在地上，灯芯一直亮着。": "The night lamp settles on the floor, its wick still burning.",
    "源格里什么也没有可搬的东西。": "There is nothing in the source cell to move.",
    "虹吸管架好了——它每回合替你搬一点（{mode}）。":
        "The siphon is set across the gap—it carries a little for you each round ({mode}).",
    "折叠虹吸管展开，架在源与出口之间。":
        "The folded siphon opens up, bridging the source and the outlet.",
    "那里已经立着东西了。": "Something is already standing there.",
    "封住这里就断了唯一的路——换个地方。":
        "Sealing this would cut the only path—try somewhere else.",
    "蜡从管口挤出来，堆成了一堵墙（完整度 {n}）。":
        "Wax squeezes out of the tube and piles into a wall (integrity {n}).",
    "应急蜡封挤成了一堵蜡墙。": "The emergency wax seal becomes a wall of wax.",
    "没有方向，线抽不出去。": "No direction, so no wire can be fed out.",
    "那个方向没有能割开的东西。": "There is nothing to cut in that direction.",
    "细线绷紧，咬住了 {n} 处挡路的东西。":
        "The wire pulls taut and bites into {n} things in the way.",
    "线抽了出去，绷在那几处障碍上。": "The wire runs out, stretched across those obstacles.",
    "两条折好的路接上了——走过去比绕远路近。":
        "The two folded paths join up—walking it beats going the long way round.",
    "折好的逃生通道铺开了。": "The folded escape route is laid out.",
    "一圈安静罩住你——穿过它的声音会再哑一分。":
        "A circle of quiet settles over you—sound crossing it goes hoarse again.",
    "最后一圈安静铺开了。": "The last circle of quiet is spread out.",
    "薄壁瓶碎了，白雾漫开（放出 {n} 单位液氮）。":
        "The thin bottle shatters and the white fog spreads ({n} units of liquid nitrogen released).",
    "冬天的样本碎开，白雾漫开。": "The winter sample shatters, white fog spreading.",
    "雷暴信落地，封口还在慢慢渗出电荷。":
        "The storm letter lands, its seal still leaking charge.",
    "未寄出的雷暴落在地上，开始渗出电荷。":
        "The unsent storm hits the ground and begins to leak charge.",
    "瓶口的引信亮了起来——还有两回合。": "The fuse at the bottle mouth lights—two rounds left.",
    "瓶装天亮落在地上，引信亮着。": "The bottled sunrise lands, its fuse burning.",
    "夜班灯被火吞了——那点光灭了。": "Fire swallowed the night lamp—the light is gone.",
    "夜班灯又咳了一声——声音还在原处。": "The night lamp coughs again—the sound stays where it was.",
    "灯芯烧到尽头，夜班灯熄了。": "The wick burned out and the night lamp went dark.",
    "管子停转了——源干了，或者出口已经满了。":
        "The tube stopped—either the source ran dry or the outlet is full.",
    "虹吸管灌满了，撤了下来。": "The siphon filled up and was taken down.",
    "蜡墙化完了——地上留下一摊熔蜡。": "The wax wall melted away—a pool of wax left on the floor.",
    "蜡墙化不动了——四周已经没有能放蜡的地方。":
        "The wax wall cannot melt—there is nowhere left around it to put the wax.",
    "线抽完了，绷紧的细线松了。": "The wire ran out and the taut line went slack.",
    "折好的通道松开了。": "The folded route came apart.",
    "雷暴在绝缘的地面上散了——没能放出电弧。":
        "The storm dissipated on insulating ground—no arc came out of it.",
    "雷暴放电，电弧顺着导电的记忆液窜过去（{n} 个失控意识挨了这一记）。":
        "The storm discharges; the arc runs through the conductive memory-liquid ({n} runaway "
        "consciousnesses caught it).",
    "最后一圈安静散了。": "The last circle of quiet faded.",
    "瓶口炸开——天亮开始往外倒。": "The bottle mouth bursts—the sunrise starts pouring out.",
    "天亮烧了起来（点燃 {n} 格）。": "The sunrise catches fire ({n} cells lit).",
    "折好的通道把你送到了另一头（还剩 {n} 趟）。":
        "The folded route carries you to the other end ({n} crossings left).",
    "误点的夜班灯": "The Mis-clocked Night Lamp",
    "那口气把你身上黏着的东西冲淡了。":
        "That breath washes away what was clinging to you.",
    "你身上没有可洗的东西——这一口只是暖了暖。":
        "There was nothing to wash off you—that breath only warmed you.",
}
