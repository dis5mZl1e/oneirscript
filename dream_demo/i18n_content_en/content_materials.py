"""英文语言包 · 内容分册（由 scripts/_split_i18n_content.py 生成）。

材料包 v1 与 SEP18 材料批次英文。
键仍是中文原文；合并进 EN 的顺序见 dream_demo/i18n.py 末尾。
"""

from __future__ import annotations




# ---- 材料反应产物批次（2026-09-18）：新液体/气体名 ----
# ---- 内容扩展包 v1（2026-09-20）：新材料/植物/地板/征兆 ----
EN_MATERIALS_PACK_V1: dict[str, str] = {
    "电解黏液": "Electrolyte Slime",
    "液化的回声": "Liquefied Echo",
    "记忆泡沫": "Memory Foam",
    "安眠树脂": "Soporific Resin",
    "磁化液态记忆": "Magnetized Liquid Memory",
    "显像墨": "Revealing Ink",
    "逐光溶液": "Light-Chasing Solution",
    "凝固的尖叫": "Congealed Scream",
    "褪色雾": "Fading Fog",
    "记忆粉尘": "Memory Dust",
    "导电雾": "Conductive Mist",
    "亢奋蒸汽": "Agitated Steam",
    "死寂气团": "Dead-Silent Air",
    "虹彩雾霭": "Iridescent Haze",
    "吸光苔墙": "Light-Eating Moss Wall",
    "回魂陶俑": "Soul-Returning Terracotta",
    "镜湖板": "Mirror-Lake Panel",
    "倦怠棉垛": "Weary Cotton Stack",
    "导电铜网墙": "Conductive Copper Mesh",
    "臆造聚合墙": "Conjured Polymer Wall",
    "意识栅栏": "Mind Fence",
    "捕梦草": "Dream-Catcher Grass",
    "荆棘藤": "Thorn Vine",
    "风向标苔": "Vane Moss",
    "融蜡花": "Wax-Melting Bloom",
    "月光蕈": "Moonlight Mushroom",
    "空鼓菌": "Hollow Mushroom",
    "空鼓地板": "Hollow Floor",
    "空鼓地板发出空洞的闷响——{radius} 格内的失控意识听见了你的脚步。（悬停脚下可随时查看声响口径）":
        "The hollow floor thuds underfoot — stray consciousness(es) within {radius} tiles hear your steps. (Hover your own tile to check noise figures at any time.)",
    "压力地板": "Pressure Floor",
    "传送带·北": "Conveyor (North)",
    "传送带·东": "Conveyor (East)",
    "传送带·南": "Conveyor (South)",
    "传送带·西": "Conveyor (West)",
    "自动运转的传送带（向北）。站上不动会被推行一格；顺行省力、逆行费力。":
        "A self-running conveyor facing north. Stand still and it carries you one tile; moving with it is cheaper, against it costs double.",
    "自动运转的传送带（向东）。站上不动会被推行一格；顺行省力、逆行费力。":
        "A self-running conveyor facing east. Stand still and it carries you one tile; moving with it is cheaper, against it costs double.",
    "自动运转的传送带（向南）。站上不动会被推行一格；顺行省力、逆行费力。":
        "A self-running conveyor facing south. Stand still and it carries you one tile; moving with it is cheaper, against it costs double.",
    "自动运转的传送带（向西）。站上不动会被推行一格；顺行省力、逆行费力。":
        "A self-running conveyor facing west. Stand still and it carries you one tile; moving with it is cheaper, against it costs double.",
    "熔融蜡烛": "Molten Candle",
    "电解黏着": "Electro-Stuck",
    "回声放大": "Echo Amplified",
    "缓冲": "Cushioned",
    "安眠": "Asleep",
    "磁引": "Magnetically Pulled",
    "显像": "Revealed",
    "惊惧": "Dread",
    "恍惚": "Hazy",
    "亢奋": "Wired",
    "静默": "Mute",
    "缠住": "Snared",
    # —— 介绍与效果文案（动态取值域 EN 覆盖）——
    "还温热的一管烛泪。使用即进入投掷瞄准：落点十字五格里，本来就可燃的格子被点着，干净的地板不会自己烧起来；高浓度可燃气会被引爆。":
        "A vial of still-warm tallow. Using it opens throw aiming: of the five cells in a cross at the landing point, only those already holding flammable material catch light — clean floor will not burn on its own, and dense gas detonates.",
    "电解黏液": "Electrolyte Slime",
    "泛着细小电花的金黄黏液。蹚过：移动变黏慢，且微弱导电。":
        "Golden slime crackling with tiny sparks. Wading through: slower and faintly conductive.",
    "一句话被反复折叠成的液体。蹚过：你的声响半径 ×2。":
        "A sentence folded over and over into liquid. Wading through: your sound radius ×2.",
    "绵软的浅色泡沫。蹚过：下一次受到的创伤 −2（吸收后消散）。":
        "Soft pale foam. Wading through: your next wound deals −2 (the foam pops absorbing it).",
    "缓慢流动的绿色树脂。站上两回合会睡着，但想象力恢复很快。":
        "Slow green resin. Standing in it two rounds puts you to sleep — imagination recovers fast.",
    "拖着金属腥味的深蓝液体。站上：被缓缓拖向最近的金属固体。":
        "Deep blue liquid with a metallic tang. Standing in it: dragged toward the nearest metal.",
    "墨绿的浓液。蹚过：视野内所有异象（含伪装）显形 6 回合。":
        "Thick green ink. Wading through: all anomalies in sight (disguised included) are revealed for 6 rounds.",
    "明亮、轻快，自己会流向视野里最亮的光源。":
        "Bright and quick — it flows by itself toward the brightest light in view.",
    "暗红色的半凝固块。蹚过：心智流失，感官却变得敏锐。":
        "Dark-red semi-solid clots. Wading through: mind drains, but your senses sharpen.",
    "灰白的雾。吸入：显影格暂时失效 4 回合，地图读数退回未知。":
        "Greyish fog. Inhaled: developed tiles stop working for 4 rounds — map readings revert to unknown.",
    "淡紫色的细尘。吸入：视野 −1，但想象力恢复 +1/回合。":
        "Pale-violet dust. Inhaled: vision −1, but imagination recovers +1 per round.",
    "青色的、带刺痒感的雾。吸入：受到的传导冲击 ×2；可燃。":
        "Cyan, prickly mist. Inhaled: shock damage taken ×2; flammable.",
    "橙色的兴奋剂蒸汽。吸入：动作加速，但清醒 −1/回合。":
        "Orange stimulant steam. Inhaled: actions speed up, but lucidity −1 per round.",
    "浓重的暗色气团。吸入：你的声音半径归零，警戒无法传播。":
        "Heavy dark air. Inhaled: your sound radius drops to zero; alerts cannot spread.",
    "流转着虹光的粉雾。吸入：低心智失真加重一档，但崩解度 +2/回合。": "Pink haze shimmering with rainbow light. Inhaled: low-mind distortion worsens a tier, but dissolution +2 per round.",
    "流转着虹光的粉雾。吸入：低心智失真加重一档，但崩解度获取 +2。":
        "Pink haze shimmering with rainbow light. Inhaled: low-mind distortion worsens a tier, but dissolution gain +2.",
    "覆盖深绿苔膜的墙，吃掉周围的微光：相邻格视野判定 −1。":
        "A wall filmed with deep-green moss that eats faint light: adjacent vision −1.",
    "一尊上釉的陶俑。破坏时会放出一只你曾解决过的异象残影。":
        "A glazed terracotta figure. Breaking it releases an echo of an anomaly you already destroyed.",
    "冰蓝的透明板。弹体命中即被镜面反弹，改变弹道。":
        "Ice-blue transparent panel. Projectiles ricochet off its mirror surface, changing course.",
    "堆到齐腰的棉垛。贴近每 3 回合想象力 −1；可以推倒清空。":
        "A waist-high stack of cotton. Nearby: imagination −1 every 3 rounds; can be pushed flat.",
    "铜丝织成的网墙。逻辑固体的天然放大器：电线信号 +4 格。":
        "A wall of woven copper wire. A natural logic amplifier: wire signals carry +4 tiles.",
    "凭空凝聚出来的墙。硬度不高、可以推，也可以徒手砸开。":
        "A wall conjured out of nothing. Soft — push it or smash it bare-handed.",
    "半透明的栅栏。撑不了太久：10 回合后自行消散。":
        "A translucent fence. It won't last: dissolves on its own after 10 rounds.",
    "叶片会主动卷合的草。踩踏：被缠住，下回合无法移动。":
        "Grass whose blades curl around you. Stepping on it: snared — no moving next round.",
    "挡视线的高棘藤。穿越：受 1 点清醒创伤。":
        "A tall bramble that blocks sight. Pushing through: take 1 lucidity damage.",
    "苔尖永远偏向最近的异象。贴近读数显示大致方位。":
        "Moss whose tips lean toward the nearest anomaly. Nearby readings show its rough bearing.",
    "暖黄发光的蜡质花。拔除：获得 1 件「熔融蜡烛」液体弹。":
        "A warm-glowing waxy bloom. Uproot it for one Molten Candle firebomb.",
    "暗白色的冷调蘑菇（蘑菇的换色变体，机制相同）。":
        "A cold pale-white mushroom (a recolored variant; mechanics identical).",
    "暖褐色的蘑菇（换色变体，机制相同）。":
        "A warm-brown mushroom (recolored variant; mechanics identical).",
    "敲上去空空的地板。踩踏发出空洞闷响，把附近的异象引来。":
        "A floor that sounds hollow. Stepping on it thuds dully, drawing nearby anomalies.",
    "微微凸起的方形地砖。踩上/离开都会向相连的机关发信号。":
        "A slightly raised square tile. Stepping on or off it signals any linked mechanism.",
    "电解黏着": "Electro-Stuck",
    "黏液导电又拉丝：移动额外耗时 +0.3。":
        "The slime clings and crackles: moves cost +0.3 extra time.",
    "回声在液面下反复折叠：你的声响半径 ×2。":
        "Echoes fold under the surface: your sound radius ×2.",
    "凝固的尖叫在你脑中反复播放：心智流失，感官却格外敏锐。":
        "The congealed scream replays in your skull: mind drains, senses sharpen.",
    "粉尘落进呼吸：视野发糊，念头却自己冒出来。":
        "Dust settles into your breath: vision blurs, ideas surface on their own.",
    "蒸汽烧进肺里：动作变快，清醒一点点烧掉。":
        "The steam burns going down: you quicken while lucidity slowly burns away.",
    "空气吞掉了所有声响：你的声音半径降到最低。":
        "The air swallows every sound: your noise radius drops to the minimum.",
    "草叶卷住了脚踝：这一回合挪不动步。":
        "Blades coil around your ankle: no moving this round.",
    "倦怠": "Weariness",
    "吸光（视野衰减）": "Light-eating (vision decay)",
    "将散的栅影": "A fence about to scatter",
    "微麻": "Tingly",
    "新凝的梦质": "Freshly dreamed matter",
    "映像": "Reflection",
    "陶土气息": "Earthen scent",
}

EN_MATERIALS_SEP18: dict[str, str] = {
    "台面下藏着机关：取走台面物品或回应其上事件的瞬间触发。外观与普通石台完全一致。":
        "A mechanism hides beneath: taking its loot or answering an event on it springs the trap. Looks exactly like a plain table.",
    "与陷阱石台同形的良性机关：触发的是开门、点亮、显影一类效果。":
        "A benign mechanism shaped like the trap table: it opens doors, lights obelisks, develops terrain.",
    "墙上的符文在感知半径内出现失控意识时发光，向相连的机关发出信号。":
        "Its runes flare when a stray consciousness enters sensing range, signalling linked mechanisms.",
    "按固定节拍摆动的机关轮：每到整点向相连的机关发一次信号。":
        "A mechanism wheel swinging on a fixed beat: it signals linked mechanisms on every stroke.",
    "由机关驱动的门：收到信号即开/关切换。外观与普通门一致、仅色差。":
        "A mechanism-driven door: each signal toggles it open or closed. Looks like a plain door, only the tint differs.",
    "收到信号后点亮，永久显影周围的地形。隐藏的奖励机关。":
        "Lights up on signal, permanently developing the surrounding terrain. A hidden reward.",
    "收到信号即升降栅栏，把人关进小格或放出来。":
        "Raises or lowers bars on signal — caging or releasing whoever stands nearby.",
    "收到信号时松开簧片，把上方的生物沿弹道推出三格。":
        "Releases its springs on signal, hurling the creature on it three tiles downrange.",
    "收到信号时向相邻格释放储备的液体或气体。":
        "Releases its stored liquid or gas into adjacent tiles on signal.",
    "收到信号即发出全图可闻的警报，召集本层的失控意识。":
        "Sounds a layer-wide alarm on signal, summoning every stray consciousness.",
    "褪色吸入": "Fading inhalation",
    "恍惚吸入": "Hazy inhalation",
    "传导吸入": "Conductive inhalation",
    "静默吸入": "Mute inhalation",
    "迷幻吸入": "Trippy inhalation",
    # 扩展包 v1：16 新异象名与描述
    "噩梦牧者": "Nightmare Herder",
    "回声抄写员": "Echo Scribe",
    "墨水瓶守卫": "Ink-Bottle Guard",
    "失眠的闹钟": "Insomniac Alarm",
    "字幕组": "Subtitle Crew",
    "强烈异象·巡回放映队": "Strong · Touring Projection Crew",
    "强烈异象·无字校对员": "Strong · Wordless Proofreader",
    "强烈异象·深渊量尺": "Strong · Ruler of the Abyss",
    "强烈异象·长镜头导演": "Strong · One-Take Director",
    "慢速放映机": "Slow Projector",
    "折返跑者": "Shuttle Runner",
    "摇篮曲哼唱者": "Lullaby Hummer",
    "裂隙剪": "Rift Shears",
    "焚焰歌者": "Pyre Singer",
    "未拆的礼盒": "Unopened Gift",
    "雾喘": "Fogbreath",
    "无眠更夫": "Sleepless Watchman",
    "查票员": "Ticket Inspector",
    "盆栽看守": "Potted Keeper",
    "遗忘档案员": "Oblivion Archivist",
    "它不看你，只看你的票。没有票的人要从身上补一张出来。":
        "It doesn't look at you — only your ticket. Those without one pay from their pockets.",
    "它自己也睡不着，所以谁也别想睡。": "It can't sleep either, so nobody gets to.",
    "它经过的地方草会长高。它也躲在长高的草里。":
        "Grass grows tall where it passes. It hides in the tall grass it grows.",
    "它给整个梦境配字幕——配得不太好。": "It subtitles the whole dream — badly.",
    "它抄写你的一举一动——连你的急躁也一起抄下来。":
        "It copies your every move — including your impatience.",
    "指尖涂着防滑的石墨粉。出手比常人快半拍（攻击基础耗时 −0.2）。":
        "Fingertips coated in anti-slip graphite. You swing half a beat faster (attack base cost −0.2).",
    "双刃错开半拍落下的剪刀——一次挥动是两道口子（近战两段）。":
        "Two blades falling half a beat apart — one swing, two cuts (melee strikes twice).",
    "它唱到高音处，梦境就跟着着一点火。它以为那是掌声。":
        "At the high notes the dream catches a little fire. It thinks that's applause.",
    "每个盒子里都是没拆开的失望——拆开的那一下格外响。":
        "Every box holds an disappointment no one unwrapped — and opening one is especially loud.",
    "它的每一次呼吸都比上一口更潮，梦里因此有了雾。":
        "Each breath is damper than the last — that's why the dream has fog.",
    "它放映的每一帧都比现实慢半拍，你也被拖进了那帧。":
        "Every frame it projects runs half a beat late — and drags you into that frame.",
    "它冲刺、折返、再冲刺——永远跑不完自己的往返跑。":
        "It sprints, turns, sprints again — a shuttle run it can never finish.",
    "它归档一切——包括你刚刚还记得的名字。":
        "It files everything away — including the names you remembered a moment ago.",
    "它不放羊。它放的是噩梦，一头头都喂得很饱。":
        "It herds no sheep. It herds nightmares, each one well fed.",
    "它打更从不出错——所以你逃到哪它都敲得到。":
        "Its night rounds are never wrong — so it can knock wherever you flee.",
    "别在狭窄的地方打碎它——它就是为这个被造出来的。":
        "Don't shatter it in a tight space — that's exactly what it was made for.",
    "曲子不难听，难的是在曲子里把念头集中起来。":
        "The tune isn't ugly; what's hard is concentrating inside it.",
    "本体在放映，僚机在收票——你们是同一场噩梦的两个岗位。":
        "The main body screens; the usher collects. Two posts of the same nightmare.",
    "一镜到底，四格之内不许剪。": "One continuous take — no cuts within four tiles.",
    "它不用红笔。它直接把你的招式涂黑。":
        "It uses no red pen. It simply blacks out your moves.",
    "它量的是你和深渊之间的距离——然后帮你缩短。":
        "It measures the distance between you and the abyss — then kindly shortens it.",
    "陈年档案的灰呛进肺里：每 3 回合清醒 −1、视野 −1。":
        "The dust of old archives chokes your lungs: every 3 rounds lucidity −1, vision −1.",
    # 扩展包 v1 异象行为层
    "「{name}」被墨迹涂黑了（剩 {turns} 回合）。": "「{name}」is blotted out in ink ({turns} rounds left).",
    "墨水瓶碎了——黑墨溅了一地。": "The ink bottle shatters — black ink splatters across the floor.",
    "命中附加：{name}（{n} 回合）。": "On-hit: {name} ({n} rounds).",
    "它涂掉了你的一个构想——墨迹 5 回合后才干透。": "It blacks out one of your conceptions — the ink takes 5 rounds to dry.",
    "{enemy}没收了你的{item}——票根掉在它脚下。": "{enemy} confiscates your {item} — the stub drops at its feet.",
    "深渊收拢了它的量尺——你被拉近了。": "The abyss gathers its ruler — you are dragged closer.",
    "一道凝视穿透长镜，正中你。": "A gaze bores through the long lens and hits you.",
    "闹钟炸响——{n} 个沉睡的异象被震醒了！": "The alarm detonates — {n} sleeping anomalies jolt awake!",
    "摇篮曲在你耳边打转——想象力停止回流。": "The lullaby circles your ears — imagination stops flowing back.",
    "墨迹干透——「{name}」重新可用了。": "The ink dries — 「{name}」 is usable again.",
    # 扩展包 v1 补完 B：构想/洞察/装备/材料消息
    "你把自己封进了三回合的凝滞里——时间在你体表结成壳。":
        "You seal yourself in three rounds of stasis — time crusts over your skin.",
    "你的轮廓融进了梦里：3 回合内异象看不见你。":
        "Your outline melts into the dream: anomalies can't see you for 3 rounds.",
    "记忆倒带——你回到了三回合前的位置。":
        "Memory rewinds — you return to where you stood three rounds ago.",
    "三回合前的位置已经回不去了——那里现在站不下。":
        "Where you stood three rounds ago won't take you back — no room there now.",
    "火种落成一片十字，{n} 格烧了起来。": "A cross of sparks lands — {n} tiles catch fire.",
    "那里没有可点燃的东西——火种熄在了指尖。": "Nothing there to ignite — the spark dies at your fingertips.",
    "携带意象与你同频共振：8 回合内效果放大 1.5 倍。":
        "Your carried images resonate with you: effects ×1.5 for 8 rounds.",
    "你撕开一道噩梦当燃料：清醒度 −5，想象力 +{n}。":
        "You tear open a nightmare for fuel: lucidity −5, imagination +{n}.",
    "视野里没有任何逻辑固体可供短路。": "No logic solid in sight to short-circuit.",
    "短路成功——{kind}被强制触发了。": "Short circuit — the {kind} force-triggers.",
    "视野里凑不齐一对触发源与接收器——接线失败了。":
        "No trigger-and-receiver pair in sight — the rewiring fails.",
    "你改接了一条电线：触发源与接收器之间亮起了新的连线。":
        "You rewire a line: a fresh connection lights up between trigger and receiver.",
    "相邻的格子里凝出了 24 点水。": "24 points of water condense on the adjacent tile.",
    "水汽没有可以凝结的地面。": "Nowhere solid enough for the vapor to condense.",
    "你播下一片低草（{n} 格）。": "You sow a patch of low grass ({n} tiles).",
    "这里种不下任何东西。": "Nothing can be sown here.",
    "那格已经是坚实的了。": "That tile is already solid.",
    "蜡在地面上一层层堆高——封成了一格蜡化记忆墙。":
        "Wax builds up layer by layer, sealing the tile into a wax memory wall.",
    "近旁 2 格内没有可以汲取的液体。": "No liquid within 2 tiles to draw.",
    "你吸干了 {n} 点液态记忆（想象力 +2）。": "You drain {n} liquid memory (imagination +2).",
    "近旁 2 格内没有可以冻结的液体。": "No liquid within 2 tiles to freeze.",
    "液面咔咔冻结——一格冰面桥搭好了。": "The surface crackles into ice — one tile of ice bridge is laid.",
    "近旁 2 格内没有可以蒸发的液体。": "No liquid within 2 tiles to transpire.",
    "液体原地蒸腾成了{gas}。": "The liquid transpires into {gas} on the spot.",
    "相邻没有可以融蚀的墙。": "No adjacent wall to dissolve.",
    "那格已经是墙了。": "That tile is already a wall.",
    "{wall}太硬了——融蚀对它无效。": "{wall} is too hard — dissolving has no effect.",
    "{wall}在想象里融成了一摊记忆。": "{wall} melts into a puddle of memory.",
    "地势被{verb}了一个档位（{n} 格）。": "The terrain is {verb} one step ({n} tiles).",
    "这一片地势被钉住了，抬不动也压不下。": "This patch of ground is pinned down — it can be neither raised nor pressed.",
    "抬升": "raised",
    "压低": "lowered",
    "通道才能坍塌——那里已经是墙了。": "Only an open corridor can collapse — that's already wall.",
    "两壁向内坍落——碎屑堆堵住了去路。": "Both walls cave in — a rubble pile blocks the way.",
    "那格腾不出空间来凝聚墙。": "No room there to conjure a wall.",
    "一面臆造聚合墙凭空凝聚成形。": "A conjured polymer wall takes shape out of thin air.",
    "梦当场重写了这个角落——{n} 格换了模样。": "The dream rewrites this corner on the spot — {n} tiles change.",
    "凝滞把你钉在了原地（剩余 {n} 回合）。": "Stasis pins you in place ({n} rounds left).",
    "凝滞的硬壳碎裂——你重新能动弹了。": "The stasis shell cracks — you can move again.",
    "你的轮廓重新显形了。": "Your outline becomes visible again.",
    "你守在原地不动——下一次攻击蓄足了劲（创伤 +2）。":
        "You hold perfectly still — your next strike is charged (+2 damage).",
    "夜行的惯性带着你——这一步没有花时间。": "Nocturnal momentum carries you — this step costs no time.",
    "梦貘的鼻息把{target}放倒了（深眠 2 回合）。": "The tapir's breath drops {target} (deep sleep, 2 rounds).",
    "没水的笔一划——{target}身上的状态被删得干干净净。":
        "One stroke of the dry pen — {target}'s states are wiped clean.",
    "静电披风炸出一记传导冲击，反打了{target}！": "Your static poncho cracks out a shock, striking back at {target}!",
    "绝缘手套隔开了机关——你安全地绕过了陷阱。": "Your insulated gloves isolate the mechanism — you bypass the trap safely.",
    "记忆泡沫吸掉了大半冲击，啪地破了。": "The memory foam absorbs most of the blow and pops.",
    "凝滞的硬壳吸收了这一击。": "The stasis shell absorbs the hit.",
    # 玩具的回忆：青灯交换事件
    "守门的青灯": "The Warden Lantern",
    "一盏青色的小灯悬在石台上方，灯罩里缺一块透镜。":
        "A small cyan lantern hovers above the table; its shade is missing a lens.",
    "青灯照着石台——灯罩里空出一块透镜的形状。":
        "The lantern lights the table — its shade holds the empty shape of a lens.",
    "交出灯塔透镜与三件纪念品（打开通道）": "Give the Lighthouse Lens and three keepsakes (open the passage)",
    "走入镜中的门（进入梦中梦·玩具的回忆）": "Step into the mirrored door (enter Memories of Toys)",
    "通道尚未打开——青灯还缺它的透镜与祭品。": "The passage is sealed — the lantern still wants its lens and offerings.",
    "青灯亮了一格——从行囊里挑出三件纪念品吧。": "The lantern brightens a notch — pick three keepsakes from your bag.",
    "青灯吞下透镜与三件纪念品——石台中央裂开了一道门。":
        "The lantern swallows the lens and keepsakes — a door splits open at the table's center.",
    "你没有灯塔透镜——青灯不肯亮。": "You have no Lighthouse Lens — the lantern refuses to light.",
    "纪念品不足：还需要 {n} 件易逝物或摄入物。": "Not enough keepsakes: {n} more consumables needed.",
    "祭品必须是恰好三件易逝物或摄入物。": "The offering must be exactly three consumables or ingestibles.",
    "行囊里没有灯塔透镜。": "No Lighthouse Lens in your bag.",
    "通道已经开着了。": "The passage is already open.",
    "勾选恰好三件纪念品（空格勾选）。": "Tick exactly three keepsakes (Space to tick).",
    "瓶中之门": "Bottle Door",
    "一只玻璃瓶立在门扉边，瓶口朝着你。": "A glass bottle stands by the door leaf, mouth facing you.",
    "无风的气球": "Windless Balloon",
    "一只气球拴在门把手上，不升也不落。": "A balloon tied to the door handle, neither rising nor falling.",
    "玩具的回忆": "Memories of Toys",
    "玩具箱壁": "Toy-Box Wall",
    "缺一只眼的布偶熊": "One-Eyed Teddy",
    "上弦的士兵": "Wind-Up Soldier",
    "提线木偶": "Marionette",
    "玩具的回忆·第一层。把三块会响的地板都踩一遍，门就会认得你。":
        "Memories of Toys, layer one. Step on all three rattling floor tiles and the door will know you.",
    "钟摆每十下响一次。铃声落下时，站到会咔哒的那块地板上去。":
        "The pendulum chimes every ten ticks. When it rings, stand on the tile that clicks.",
    "按亮三块地板，顺序别错。错一次，它们就全忘了。":
        "Light the three floor tiles in order. One mistake and they all forget.",
    "{name}让开了路——这一层的门认得你了（N 下潜）。":
        "{name} steps aside — this layer's door knows you now (N to descend).",
    "{name}摇了摇头——解谜还没完成。": "{name} shakes its head — the puzzle is unfinished.",
    "解谜完成——与守门人谈谈，门就会开启。": "Puzzle solved — speak with the warden and the door will open.",
    "门纹丝不动——先完成这一层的解谜，与守门人谈谈。":
        "The door won't budge — finish this layer's puzzle and talk to the warden.",
    "三块机关石台全部到位——守门人抬起头来。": "All three mechanism tables are set — the warden looks up.",
    "三块地板按序亮起——玩具箱的锁开了。": "The three tiles light in sequence — the toy-box lock opens.",
    "顺序不对——玩具箱里的齿轮重新打乱了。": "Wrong order — the gears inside the toy box reshuffle.",
    "台面下似乎藏着什么（陷阱）。": "Something seems hidden beneath the surface (trap).",
    "墙后传来轻微的心跳声……": "A faint heartbeat behind the wall…",
    "意图：{intent}": "Intent: {intent}",
    "向你扑来": "about to pounce at you",
    "正在犹豫": "hesitating",
    "尚未察觉你": "unaware of you",
    "步数：{n}": "Steps: {n}",
    "磁力拖拽着你滑向金属。": "Magnetism drags you toward the metal.",
    "棉絮吸走了你的念头（想象力 -1）。": "The cotton soaks up your thoughts (imagination -1).",
    "陶俑碎裂——一个残影从碎片中站起。": "The terracotta shatters — an echo rises from the shards.",
    "心智的崩塌波及了清醒（清醒 −1）。": "The mental collapse spreads to clarity (lucidity −1).",
    "清醒的流失侵蚀了心智（心智 −1）。": "The fading clarity erodes the mind (mind −1).",
    "棉絮吸走了你的念头（想象力 −1）。": "The cotton soaks up your thoughts (imagination −1).",
    "冲击波扫过你，清醒度 −{n}。": "The shockwave sweeps over you: lucidity −{n}.",
    "校准师": "Calibrator",
    "把立方体推到标记的位置上——它们会告诉你对错。": "Push the cubes to the marked spots — they'll tell you right from wrong.",
    "推错了？没关系。我可以帮你重置，但你需要重新开始。": "Pushed wrong? No worries. I can reset it for you — but you'll start over.",
    "规整的纯白立方体。可以推动，但无法破坏——推到标记位置上。":
        "A pristine white cube. Pushable but indestructible — push it to the marked spot.",
    "门扉之壁": "Wall of Door-Leaves",
    "刚从两壁坍落下来的碎块，堆得歪歪斜斜。可以砸开。": "Freshly caved-in debris, heaped crooked. Can be smashed open.",
    "碎屑堆": "Rubble Pile",
    "理念立方体": "Idea Cube",
    "规整的纯白立方": "A pristine white cube",
    "合辙枢": "AND Gate",
    "分流枢": "OR Gate",
    "接线枢": "Junction Box",
    "两道齿轨咬合": "Two gear-racks meshing",
    "单向的绿色阀芯": "A one-way green valve",
    "电路逻辑门：本回合收到 2 个以上不同来源的信号才向下游转发。":
        "A logic gate: forwards downstream only when 2+ distinct sources signal this round.",
    "电路逻辑门：收到任意信号即以满强度向下游转发。":
        "A logic gate: any signal re-emits downstream at full strength.",
    "四通接线盒：信号原样穿过，便于跨格布线。":
        "A four-way junction box: signals pass straight through for easy routing.",
    "四通的马蹄钉": "A four-way staple",
    "新崩落的碎屑": "Freshly collapsed debris",
    # 梦中梦·门之回廊：异象/物品
    "拟门": "Door Mimic",
    "你以为那是出口。它也以为你是钥匙。": "You thought it was the exit. It thought you were the key.",
    "门扉守卫": "Door Warden",
    "它记得每一扇门的锁孔形状，也记得每一个没敲门的人。":
        "It remembers every keyhole's shape — and everyone who never knocked.",
    "回廊烛台": "Corridor Candelabrum",
    "无门之环": "Ring Without a Door",
    "门之钥": "Key of Doors",
    "门枢齿轮": "Door-Hinge Gear",
    "冰冷的钥匙，齿痕像一排合拢的门。使用它，走进不存在的门。":
        "A cold key whose teeth look like a row of closed doors. Use it and step through a door that isn't there.",
    "从圣所门轴上卸下的齿轮：握着它，门开得格外顺滑（视野 +4）。":
        "A gear lifted from the sanctum's hinge: doors swing smooth in your grip (vision +4).",
    "回廊里唯一的光。掷出去，炸成一圈更旺的火。":
        "The only light in the corridor. Throw it — it bursts into a fiercer ring of fire.",
    "没有门框的环。戴着它，每一次崩解都推得更深（崩解推进 +4）。":
        "A ring with no frame. Wear it and every dissolution digs deeper (dissolution gain +4).",
    "无数门的呼吸": "The breathing of countless doors",
    "圣所门槛上渗出的泪。蹚过：想象力每 4 回合 +1。": "Tears seeping from the sanctum threshold: imagination +1 every 4 rounds.",
    "门之泪": "Door Tears",
    "门槛的泪水浸湿鞋底：想象力每 4 回合 +1。": "Tears at the threshold soak your soles: imagination +1 every 4 rounds.",
    "风向感应": "Vane Sense",
    "苔尖指过方向的直觉留在你眼里：视野 +1。": "The moss's sense of bearing stays in your eyes: vision +1.",
    "门扉眩晕": "Door Vertigo",
    "门缝里灌进来的风让你看什么都歪：视野 −2。": "Wind through the door cracks bends your sight: vision −2.",
    "门缝里渗出的冷风。吸入：视野 −2，看什么都歪。": "Cold wind seeping through door cracks: vision −2, everything tilts.",
    "致盲": "Blinded",
    "强光把眼前的字洗成一片白：普通视觉归零 2 回合，单轮最长 3 回合。听觉、灵视与传信不受影响，光源也照不回来。":
        "Bright light washes the words before you into white: plain sight drops to 0 for 2 rounds, hard-capped at 3 rounds per acquisition. Hearing, spirit sight and messaging are untouched, and light sources cannot bring sight back.",
    "门隙之风": "Draft of Door-Cracks",
    "门扉眩晕吸入": "Vertigo inhalation",
    "{item}对不上任何一扇门。": "{item} fits no door at all.",
    "你已经在梦中梦里——先从第 1 层上浮出去。": "You are already inside the dream-within-dream — surface from layer 1 first.",
    "钥匙在锁孔里转了半圈——你侧身走进了一扇不存在的门。":
        "The key turns halfway in the lock — you slip sideways through a door that isn't there.",
    "—— 梦中梦·{name} 第 1 层 ——": "—— Dream-within-dream · {name}, Layer 1 ——",
    "你从门里退了出来——{name}在你身后合拢。": "You back out of the door — {name} folds shut behind you.",
    "你退回上一层门廊：梦中梦·{name} 第 {n} 层。": "You retreat to the previous corridor: Dream-within-dream · {name}, layer {n}.",
    "你又穿过一扇门：梦中梦·{name} 第 {n} 层。": "You pass through another door: Dream-within-dream · {name}, layer {n}.",
    "{name}的最深处——门在这里只剩墙的形状。": "The deepest reach of {name} — here the doors are only the shape of walls.",
    "第 20 个强烈异象崩解了——它的残骸里留下一把冰冷的「门之钥」。":
        "The 20th strong anomaly dissolves — a cold Key of Doors remains in its wreckage.",
    "门之回廊的墙体。无数扇门在它的纹理里开开合合，谁也没走进去。":
        "The wall of the Door Corridor. Countless doors open and close in its grain; no one has ever walked through.",
    "梦中梦入口": "Dream-within-dream entrance",
    "陷阱石台": "Trap Table",
    "机关石台": "Mechanism Table",
    "共鸣报警器": "Resonant Alarm",
    "囚笼栅栏": "Cage Post",
    "定时摆轮": "Pendulum Timer",
    "弹射座": "Launcher Pad",
    "感应符文墙": "Rune Sensor Wall",
    "显影方尖": "Revealing Obelisk",
    "机关门": "Mechanism Door",
    "灌注阀": "Infusion Valve",
    "导电铜网墙": "Conductive Copper Mesh",
    "冷硬的栅柱": "Cold hard bars",
    "方尖上的微光": "A faint glow on the obelisk",
    "符文微光流转": "Runes shimmering faintly",
    "绷紧的簧片": "Taut springs",
    "规律的滴答声": "A regular ticking",
    "阀门的潮气": "The valve's damp breath",
    "随时会啸叫的铜喇叭": "A brass horn ready to shriek",
    "齿轮咬合的门": "A door of meshing gears",
    "荆棘刮过手臂：清醒度 −{n}。": "The thorns scrape your arm: lucidity −{n}.",
    "咔哒一声——什么也没有发生。": "A click — and nothing happens.",
    "石台深处传来咔哒一声——然后什么也没有发生。": "A click deep inside the table — then nothing.",
    "机关门转动齿轮，{state}。": "The mechanism door grinds its gears, {state}.",
    "打开": "opening",
    "关上": "closing",
    "显影方尖亮起——周围的地形从黑暗里显形。": "The obelisk lights up — the surroundings develop out of the dark.",
    "囚笼栅栏升起——四周竖起了半透明的栅影。": "Cage posts rise — translucent bars spring up around you.",
    "囚笼栅栏降下——栅影散去。": "The cage posts lower — the bars scatter away.",
    "弹射座松开簧片——一股力量把人推了出去。": "The launcher releases — a force hurls you away.",
    "灌注阀开启——{material}涌了出来。": "The valve opens — {material} comes flooding out.",
    "共鸣报警器发出刺耳的长鸣——整层的梦都被惊动了。": "The resonator blares a piercing alarm — the whole layer stirs.",
    "石台下的机关咬合——{n} 个失控意识被召唤出来！": "The mechanism under the table engages — {n} anomalies are summoned!",
    "石台震了震，但没有东西被召唤出来。": "The table shudders, but nothing comes.",
    "石台四周弹起栅栏，把你困在中间——栅影看起来撑不了多久。": "Bars spring up around you, caging you in — they look like they won't last.",
    "石台缝隙里涌出一团{gas}！": "A cloud of {gas} pours from the table's seams!",
    "石台弹出一枚弩箭，正中你：心智 −{d}。": "The table fires a bolt — it hits you: mind −{d}.",
    "石台弹出一枚弩箭，擦着空气飞走了。": "The table fires a bolt that whistles past you.",
    "石台上的符文亮起——一股阴冷的战栗爬上脊背。": "Runes on the table flare — a cold shiver crawls up your spine.",
    "地面隆起凝硬——退路被堵住了几格。": "The ground swells and hardens — your retreat is blocked in places.",
    "{label}亮了一下，周围的地形显形了。": "{label} flashes — the surrounding terrain develops.",
    "{label}里流出温热的念头：想象力 +{n}。": "Warm thoughts flow from the {label}: imagination +{n}.",

    "蜜酿": "Honeybrew",
    "定影墨": "Fixed Ink",
    "蚀金浆": "Gilt-Etching Slurry",
    "血蜡膏": "Bloodwax Salve",
    "蜜灰膏": "Honey-Ash Paste",
    "蚀骨瘴": "Bone-Etching Miasma",
    "无意识低语": "Unconscious Whisper",
    "核心执念·执笔者": "Core Obsession · The Scribe",
    "蓄电": "Piezo Charge",
    "身上积着压电地板的电荷：层数越高，离放电越近。": "Piezo charge gathered from the floor: the more stacks, the closer the discharge.",
    "玻璃瓶": "Glass Bottle",
    "理想试管": "Ideal Test Tube",
    "气球": "Balloon",
    "理想气体容器": "Ideal Gas Vessel",
    "耐热的空瓶：可以盛装本格的一种液态记忆（上限 30），再倒回任何一格。": "A heat-proof empty bottle: holds one kind of liquid memory from this cell (cap 30), pourable back onto any cell.",
    "互不相侵的理想容器：可同时分装多种液态记忆而互不反应（合计上限 30），再逐一倒出。": "An ideal vessel with separate chambers: holds several liquid memories at once without reactions (total cap 30), pour them out one by one.",
    "扎紧口的气球：可以装本格的一种弥散印象（上限 40），再倒回任何一格。": "A tied balloon: holds one kind of diffuse impression from this cell (cap 40), pourable back onto any cell.",
    "分隔内胆的理想容器：可同时装多种弥散印象而互不反应（合计上限 40），再逐一倒出。": "An ideal vessel with separated bladders: holds several diffuse impressions at once without reactions (total cap 40), pour them out one by one.",
    "排练中的镜子": "The Rehearsing Mirror",
    "合唱团的静电": "The Choir's Static",
    "倒着下的雨": "The Upside-down Rain",
    "门后的门": "The Door Behind Doors",
    "蜡像茶会": "The Wax Tea Party",
    "撕页的图书馆": "The Page-tearing Library",
    "午夜的广播": "The Midnight Broadcast",
    "游泳的家具": "Swimming Furniture",
    "星星大甩卖": "The Star Clearance Sale",
    "木偶的彩排": "The Puppets' Rehearsal",
    "镜子里的你在反复排练一句台词，还没有轮到你。": "Your reflection rehearses one line over and over; it is not yet your turn.",
    "电流声里藏着一支合唱团，正在调音。": "A choir hides in the static, still tuning up.",
    "雨从地面升回云端，每一滴都记得你来时的路。": "Rain rises from the ground back to the clouds; every drop remembers the road you came by.",
    "一排门在走廊两侧反复出现，每一扇都通向下一扇。": "Doors repeat themselves along both sides of the hall, each opening onto the next.",
    "蜡化的客人们围坐一桌，茶壶里的蜡还在倒。": "Wax-stiffened guests sit around a table while the teapot keeps pouring.",
    "一本书在半空自己撕自己，纸页雪片般落下。": "A book tears itself apart mid-air, pages falling like snow.",
    "老式喇叭里在念一篇没有署名的稿件。": "An old loudspeaker reads an unsigned manuscript aloud.",
    "房间进了半米深的梦水，家具们正在仰泳。": "The room has flooded half a meter deep with dreamwater, and the furniture is doing the backstroke.",
    "天上贴着海报：星星十颗起步，概不退换。": "A poster on the sky reads: stars on sale, packs of ten, no returns.",
    "木偶们自己排练一出没有观众的戏。": "Puppets rehearse a play with no audience of their own accord.",
    "打字机长着人的形状，按键声细密如雨。它已经在替你写了——连结尾都替你挑好了。": "A typewriter shaped like a person, its keys pattering like rain. It has already been writing for you — even the ending is chosen.",
    "瓶颈塞着布条的油瓶。使用就是投掷：落点十字五格先泼上燃油再一起点着，斜角四格只烧本来就可燃的——整片 3×3 火海。已有液体的地面不另铺油，防火层点不着。": "An oil bottle corked with rag. Using it means throwing: the five cells of a cross at the landing point are doused in fuel oil and light together, while the four diagonals burn only if they were already flammable — a 3×3 fire sea. Ground that already holds liquid gets no extra oil, and fireproof tiling will not catch.",
    "胶囊在指缝间微微发烫，像一颗急着出生的雷。掷出即可引爆；爆破扳指能撑大它的脾气。": "The capsule warms between your fingers like a thunderclap eager to be born. Throw to detonate; the Blast Ring widens its temper.",
    "一只耐热的空瓶，瓶口还留着上一位使用者的指纹。盛一种液态记忆，至多二十五点，倒在任何你想倒的地方。": "A heat-proof empty bottle, the rim still fingerprinted by its last user. Holds one liquid memory, thirty points at most, poured wherever you please.",
    "管腔彼此隔开，像几段互不打听的心事。多种液态记忆可同时盛放而互不沾染，合计二十五点，倒出时先后由你。": "Separate chambers, like secrets that never ask after each other. Several liquid memories coexist untouched, thirty points total, released in any order you choose.",
    "气球绷得紧紧的，里面关着一口抓来的弥散印象——至多二十五点。解开扎口，它就回到你想让它去的地方。": "The balloon strains at its knot, holding a captured breath of impression — forty points at most. Untie it, and it goes wherever you send it.",
    "内胆一层隔一层，各装各的气，谁也不碰谁。合计二十五点，放气时一次一种，次序由你。": "Bladders layered apart, each holding its own air. Forty points total, released one kind at a time, in your order.",
    "撕开封纸的一瞬，光把整片视野填满：此刻你看得见的敌对意识都会被晃得视距减半，五回合才缓过来。墙后面的不受影响，近处的仍能看见你。": "The instant the wrapper tears, light floods your whole field of view: every hostile mind you can see has its sight halved for five rounds. Nothing behind a wall is touched, and close ones can still make you out.",
    "表盘上本该是数字的位置刻着一圈燃点。指针指向哪里，哪里的火就烧得更任性（点燃强度 +1）。": "Where the numerals should be, the dial is ringed with kindling points. Wherever the hand rests, the fire burns wilder (+1 ignition strength).",
    "啼哭散尽后留在襁褓里的最后一点温度。它替你记着你的名字（免疫失忆，跨局保留）。": "The last warmth left in the swaddle after the first cry faded. It remembers your name for you (immune to forgetting; persists across runs).",
    "想象自己在梦的中心点燃——火以你为圆心开花，半径三、威力三。花瓣落尽，你仍站在火里；爆炸与点燃敌我共担，注意自身清醒与灼烧风险。": "Imagine yourself lit at the center of the dream — fire blossoms around you, radius three, power three. When the petals fall you are still standing in the fire; blast and ignition affect allies and enemies alike — watch your own clarity and burning risk.",
    "薄荷的凉意直上眉心：滞留期间每两回合沁出一点清醒，共十四点。": "Mint coolness rises to the brow: while it lasts, one clarity seeps in every two rounds, fourteen in all.",
    "敲击｜每 6 拍向以自身为中心 9×9 范围的异象告知你的位置。": "Knock | every 6 beats it tells every anomaly in a 9×9 area where you are.",
    "回声广播｜每 7 拍把你的位置告知它视野内的同伴。": "Echo Broadcast | every 7 beats it tells nearby anomalies your position.",
    "代笔｜每 8 拍抽走你 2 点想象力，且不会陷入失明。": "Ghostwrite | every 8 beats it drains 2 imagination; it cannot be blinded.",
    "遗忘之触｜命中你时，随机驱散你的一个正面征兆。": "Touch of Forgetting | on hit it randomly dispels one of your boons.",
    "循迹重生｜被解决后有概率在远处重新凝聚成形。": "Trace Rebirth | may re-form far away after being resolved.",
    "纸折护身｜受到的创伤 −1（至少 1 点）。": "Paper Fold | trauma taken −1 (min 1).",
    "顺势推挤｜攻击时 33% 概率把你沿攻击方向推开一格。": "Momentum Push | 33% chance to shove you one cell along the attack.",
    "嘲讽｜它视野内的异象受到创伤时，伤害转移给它自己。": "Taunt | trauma dealt to anomalies within its vision is redirected to it.",
    "迟缓行进｜每 2 回合移动 1 格，但攻击节奏正常。": "Slow Advance | moves one cell every 2 rounds; attacks on schedule.",
    "追光｜一旦盯上你，失去视线也不会很快跟丢。": "Light-chaser | once it marks you, losing sight barely slows it.",
    "自我修订｜每 5 拍恢复 1 点完整度。": "Self-revise | regains 1 integrity every 5 beats.",
    "空间挪移｜受击后有概率挪移到附近另一处。": "Spatial Shift | may blink to a nearby spot after being hit.",
    "织梦同调｜身旁有同伴时，造成的创伤 +1。": "Dream-weave | +1 trauma while a fellow anomaly stands beside it.",
    "逐客｜它不遭受任何迟缓、冻结类侵扰。": "Turn-away | suffers no sluggish or freeze afflictions.",
    "原初不息｜免疫迟缓与冻结，也不会被推动。": "Primordial Vigor | immune to slow and freeze; cannot be pushed.",
    "初啼｜受到创伤时发出啼哭，惊动整层梦。": "First Cry | crying out when wounded, waking the whole layer.",
    "定稿免疫｜不会陷入失明，也不会被推动。": "Final-draft Immunity | cannot be blinded or pushed.",
    "技能 ": "Skill ",
    "特性 ": "Trait ",
    "孢子吃掉噩梦后剩下的空白：一片几乎看不清的雾，雾里只剩无意识在低语（虚无孢子+噩梦气息的反应产物）。": "The blank left after spores eat the nightmare: a near-opaque fog where only the unconscious keeps whispering (product of void spores + nightmare breath).",
    "电浆雾": "Plasma Mist",
    # 反应产物批次的图鉴描述
    "红酒沉了蜜：比红酒更厚更甜的琥珀色酒浆（红酒+蜂蜜的反应产物）。":
        "Honey sunk into wine: a thicker, sweeter amber liquor (product of red wine + honey).",
    "被显影液定了影的浓墨：几乎不再流动（黑墨+显影液的反应产物）。":
        "Dense ink with its image fixed by developer: barely flows at all (product of black ink + developer fluid).",
    "酸与熔金搅成的凶浆：热与蚀性并存（酸蚀液+熔念金属的反应产物）。":
        "A vicious slurry of acid and molten metal: heat and corrosion in one (product of acid etchant + molten thought-metal).",
    "封在蜡里的灵视之血：暗红黏稠，仍可点燃（灵视之血+熔融蜡烛的反应产物）。":
        "Sightblood sealed in wax: dark red and viscous, still flammable (product of sightblood + molten candle).",
    "蜂蜜粘住浮灰凝成的灰黄色膏（蜂蜜+灰尘云的反应产物）。":
        "A grey-yellow paste of honey congealed around drifting dust (product of honey + dust cloud).",
    "毒与酸喂出来的黄绿色瘴气：视野被它严重衰减（毒气+溶梦酸雾的反应产物）。":
        "A yellow-green miasma fed by poison and acid: it severely degrades sight (product of poison gas + dream-acid fog).",
    "孢子吃掉噩梦后的空白瘴：穿过它几乎看不清东西（虚无孢子+噩梦气息的反应产物）。":
        "A blank miasma left after the spores devour the nightmare: near-impenetrable to the eye (product of void spores + nightmare breath).",
    "静电落进导电液腾起的离子雾：泛着青白的微光（导电液态记忆+静电尘的反应产物）。":
        "An ionized haze rising where static falls into conductive liquid: it glimmers pale blue-white (product of conductive liquid memory + static dust).",

    # ---- 平衡批次：深层专属异象 + 新装备/消耗品/摄入物 ----
    "梦的账房": "The Dream's Accountant",
    "拨着一把看不见的算盘：它记下你花掉的每一分清醒，并打算连本带利地收回去。":
        "It clicks an invisible abacus: it records every point of lucidity you spend, and means to collect with interest.",
    "墨档员": "Ink Archivist",
    "浑身浸透墨水的登记员，替深层边界归档所有走失的名字。静止时与一摞档案没有区别。":
        "A registrar soaked through with ink, filing the lost names of the deep boundary. Standing still, it is indistinguishable from a stack of files.",
    "全声合唱": "The Full Choir",
    "所有被删掉的台词在这里合唱。与它同行者众多，且一个比一个固执。":
        "Every deleted line sings here. It travels with company — many, and each more stubborn than the last.",
    "虚无见证": "The Null Witness",
    "它见证了梦的开始，也将见证结束；它不追你——它只是必然会在。":
        "It witnessed the dream's beginning and will witness its end; it does not chase you — it is simply inevitable.",
    "速写手套": "Sketching Gloves",
    "指尖涂着防滑的石墨粉。近战与弹体伤害 +1，且出手比常人快半拍（攻击基础耗时 −0.2）。":
        "Graphite-dusted fingertips. Melee and projectile damage +1, and you strike half a beat faster (attack base time −0.2).",
    "碑文护腕": "Epitaph Wristband",
    "刻着一整圈墓志铭的旧表带：读得越熟，越分不清自己是不是碑里的人。心智创伤与清醒创伤各 −1。":
        "An old wristband engraved with epitaphs: the better you know them, the less sure you are which side of the stone you're on. Mind and lucidity trauma −1 each.",
    "逆行的沙漏": "Reversed Hourglass",
    "沙子往上落。戴它的人总觉得自己还有更多时间——清醒创伤 −2。":
        "The sand falls upward. Whoever wears it feels they have more time — lucidity trauma −2.",
    "苦艾糖滴": "Wormwood Pastille",
    "苦得皱眉的一粒糖，含化之后，梦的边缘会清楚一点点。心智 +10。":
        "A bitter lozenge; once dissolved, the edges of the dream sharpen a little. Mind +10.",
    "浓缩咖啡锭": "Espresso Tablet",
    "压得像小石头的浓缩咖啡。舌尖一麻，睡意退散：清醒度 +12。":
        "Espresso pressed into little stones. A numb tongue, and sleepiness retreats: lucidity +12.",
    "梦境电解水": "Dream Electrolytes",
    "一瓶喝不出味道的透明液体。均衡补液：清醒度 +8、想象力 +8。":
        "A bottle of tasteless clear liquid. Balanced rehydration: lucidity +8, imagination +8.",
    "聚合弹匣": "Aggregate Clip",
    "五枚压好的聚合弹，拍进掌心就能感到发射许可在皮肤下发烫。聚合弹 +5。":
        "Five pressed aggregate rounds; slap them into your palm and the fire permit warms under your skin. +5 rounds.",
    "烟花束": "Sparkler Bundle",
    "一把绑在一起的仙女棒。掷出去向八个方向各抛一束火星，最远三格——它不铺火海，是一条条烧过去。":
        "A fistful of sparklers tied together. Thrown, they fling a spark down each of eight directions, up to three cells — no sheet of fire, just eight burning lines.",
    "微型雷管": "Micro Detonator",
    "迷你版雷管：威力小些，胜在便宜、常见、舍得扔。":
        "A pocket-sized detonator: weaker, but cheap, common, and easy to part with.",
}
