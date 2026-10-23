"""英文补漏：材料反应配方（2026-10-22，E2 运行期文案审计）。

`tests/test_english_runtime_notifications.py` 用会记录 miss 的英文表真跑失败入口，
查出 189 条反应配方文本只走 `tr(recipe.message)`/`tr(recipe.note)`，静态字面量
扫描看不见：55 条触发播报、123 条图鉴说明，以及 4 个反应分类和 5 个材料/类型名。

术语沿用 `i18n_content_en` 已登记的正式名（Acid Etch、Lethe Water、Developer
Fluid、Scalding Steam…）。逐条机器初译，语气与术语仍需母语终校（E2 第 4 项）。
"""
from __future__ import annotations

EN_REACTIONS = {
    # ---- 反应分类 / 产物 / 类型（图鉴筛选用）----
    "液液反应": "Liquid-Liquid Reactions",
    "气气反应": "Gas-Gas Reactions",
    "液气反应": "Liquid-Gas Reactions",
    "其他反应": "Other Reactions",
    "熔穿": "Melt-Through",
    "蚀刻": "Etch",
    "墙体": "Wall",
    "机制": "Mechanism",
    # ---- 缺失的材料名 ----
    "干纸堆": "Dry Paper Pile",
    "防火石面": "Fireproof Stone Surface",
    "固体墙": "Solid Wall",
    # ---- 触发播报（事件记录）----
    "书页地泡了水，整片化开淌成纸浆。": (
        "The Page Ground soaks through; the whole patch dissolves into paper pulp."),
    "催眠雾溶进注射用梦水，配成温和的镇静溶液。": (
        "Hypnotic fog dissolves into injectable dream water, settling into a gentle sedative solution."),
    "回响黑曜岩被冻得脆裂开来。": (
        "The Echoing Obsidian freezes and splits apart."),
    "墨雾沉进水面，凝出一层能导电的稀墨。": (
        "Ink mist sinks into the water, thickening into a conductive thin ink."),
    "导电雾沉进水里，清水从此带了电。": (
        "Conductive mist sinks into the water; the clear water now carries a charge."),
    "干纸堆泡了水，整片塌软淌成纸浆。": (
        "The dry paper pile soaks through, slumping into paper pulp."),
    "忘川水吞掉低语，只留下稀释的记忆。": (
        "Lethe water swallows the whispers, leaving only diluted memory."),
    "忘川水洗去锚上的悔恨，它锈蚀成了一段普通的墙。": (
        "Lethe water washes the regret from the anchor; it rusts into an ordinary wall."),
    "忘川水洗掉墙上的蜡衣，墙露出了本来的面目。": (
        "Lethe water strips the wax coat from the wall, revealing what lies beneath."),
    "显像墨泼向遮蔽弥散印象，藏住的轮廓全显了形，泛成墨雾。": (
        "Revealing ink splashes over the shrouded diffuse impression; every hidden outline "
        "surfaces, blooming into ink mist."),
    "显影液冲洗褪色雾，淡去的轮廓重新显影成稀释记忆。": (
        "Developer fluid washes the fading fog; the faded outlines develop again into diluted memory."),
    "显影液漫过空白聚合物，显出普通的地面。": (
        "Developer fluid spreads across the blank aggregate, revealing ordinary ground."),
    "晨醒溶液顶开催眠雾，蒸成一缕透亮的醒素薄气。": (
        "Morning-wake solution pushes through the hypnotic fog, steaming into a wisp of clear "
        "wakefulness vapor."),
    "棋盘格地板被冻得整格碎裂。": (
        "The checkerboard floor freezes and shatters square by square."),
    "水冲塌了灰烬，地面被冲得干干净净。": (
        "Water collapses the ash, scouring the ground clean."),
    "水淋透了月壤，细尘板结退回普通地面。": (
        "Water soaks the moon soil; the fine dust packs down and reverts to ordinary ground."),
    "水淹了压电地板，短路烧毁后退回普通地面。": (
        "Water floods the piezo floor; a short circuit burns it out and it reverts to ordinary ground."),
    "水淹了梦境绒毯，绒毛塌陷退回普通地面。": (
        "Water floods the dream velvet; the pile collapses and it reverts to ordinary ground."),
    "水灌满海绵聚合物，孔泡瘫掉退回普通地面。": (
        "Water fills the sponge aggregate; the pores collapse and it reverts to ordinary ground."),
    "水银遇上辐射尘埃，蒸出一层无声的毒气。": (
        "Mercury meets radiation dust and gives off a silent layer of poison gas."),
    "水银霎时冻住，凝成一片脆亮的银冰面。": (
        "The mercury freezes at once into a brittle, gleaming sheet of silver ice."),
    "液化的回声渗进吸声聚合物，被吞得一声不剩。": (
        "Liquefied echo seeps into the sound-absorbing aggregate and is swallowed without a sound."),
    "液化的回声重新化开，雾里全是学着呢喃的回音。": (
        "The liquefied echo melts back open; the fog fills with murmuring, imitating echoes."),
    "液氮冻裂了粗糙聚合物，凸起剥落退回普通地面。": (
        "Liquid nitrogen cracks the rough aggregate; the ridges flake off and it reverts to "
        "ordinary ground."),
    "液氮冻裂了防火石面，石层崩开退回普通地面。": (
        "Liquid nitrogen cracks the fireproof stone surface; the layer splits and it reverts "
        "to ordinary ground."),
    "液氮吞下梦醚气，凝成一缕晨霜清气。": (
        "Liquid nitrogen swallows the dream-ether gas, condensing it into a wisp of morning frost."),
    "液氮浇透了灼热聚合物，烫意退尽了。": (
        "Liquid nitrogen floods the scorching aggregate; the searing heat drains away."),
    "溶梦酸雾舔蚀着玻璃幕墙。": (
        "Dissolving-dream acid mist licks at the glass curtain wall."),
    "潮解纸墙泡水化开了，淌成一汪纸浆。": (
        "The deliquescent paper wall soaks through and melts into a pool of paper pulp."),
    "潮解纸墙被冻得脆裂开来。": (
        "The deliquescent paper wall freezes and splits apart."),
    "灰尘蒙住了反光聚合物，亮面失色了。": (
        "Dust veils the reflective aggregate; its bright face goes dull."),
    "灰尘蒙住了星图地，星星一颗颗熄灭了。": (
        "Dust veils the star chart ground; the stars go out one by one."),
    "灼热蒸汽烘着安眠树脂，化出一缕安眠香。": (
        "Scalding steam bakes the soporific resin, drawing out a thread of sleep-scented fragrance."),
    "灼热蒸汽熏软了木质聚合物，地面塌回普通模样。": (
        "Scalding steam softens the wooden aggregate; the ground slumps back to its ordinary form."),
    "灼热蒸汽熨过冰面，冻层化回了普通地面。": (
        "Scalding steam irons the ice sheet; the frozen layer melts back into ordinary ground."),
    "灼热蒸汽熨过柔软聚合物，塌回普通地面。": (
        "Scalding steam irons the soft aggregate; it slumps back into ordinary ground."),
    "灼热蒸汽胀碎了空鼓地板，退回普通地面。": (
        "Scalding steam bursts the hollow floor; it reverts to ordinary ground."),
    "灼热蒸汽闷软了纸墙，纸墙瘫成了一汪纸浆。": (
        "Scalding steam steams the paper wall soft; it slumps into a pool of paper pulp."),
    "熔念金属淬进水里，硬化成一截坚硬聚合墙。": (
        "Molten ideation quenches in the water, hardening into a stretch of solid aggregate wall."),
    "玻璃幕墙被冻得脆裂开来。": (
        "The glass curtain wall freezes and splits apart."),
    "磁带墙被冻得脆裂开来。": (
        "The tape wall freezes and splits apart."),
    "纸浆吸饱催眠雾，滤出一汪镇静溶液。": (
        "The paper pulp soaks up hypnotic fog and filters out a pool of sedative solution."),
    "脑脊液滤过噩梦气息，配成一剂注射用梦水。": (
        "Cerebral fluid filters the nightmare breath into a dose of injectable dream water."),
    "色块墙被冻得脆裂开来。": (
        "The color-block wall freezes and splits apart."),
    "虚无孢子落进原初混沌，抹出一汪无念黑渊。": (
        "Void spores fall into primordial chaos, blotting out an abyss of no-thought."),
    "虹彩雾霭凝进汞面，搅成一滩彩虹牛奶。": (
        "Iridescent haze condenses onto the mercury surface, churning into a pool of rainbow milk."),
    "记忆泡沫裹住呢喃，散开成了一小汪泪水。": (
        "Memory foam wraps the murmur; as it spreads, it becomes a small pool of tears."),
    "记忆粉尘沉进水面，凝成一汪稀释记忆。": (
        "Memory dust sinks into the water, condensing into a pool of diluted memory."),
    "超临界流体剥掉了金属聚合物的镀层，退回普通地面。": (
        "Supercritical fluid strips the plating from the metal aggregate; it reverts to "
        "ordinary ground."),
    "超临界流体剥穿绝热层，分层剥落退回普通地面。": (
        "Supercritical fluid cuts through the thermal barrier; layer by layer it flakes away "
        "and reverts to ordinary ground."),
    "酒精蒸气化掉了冰面，地面退回普通模样。": (
        "Alcohol vapor dissolves the ice sheet; the ground returns to its ordinary form."),
    "酸蚀液渗进墙体，石体被蚀得熔穿。": (
        "Acid etch seeps into the wall, eating straight through the stone."),
    "静电尘溶进清水，水从此带了电。": (
        "Static dust dissolves into the clear water; the water now carries a charge."),
    "静电尘点在油面上，蒸出一蓬可燃气体。": (
        "Static dust sparks on the oil surface, raising a plume of flammable gas."),
    "麻醉雾溶进清水，水面凝出温和的镇静溶液。": (
        "Anesthetic fog dissolves into the clear water, condensing into a gentle sedative solution."),
    # ---- 图鉴说明（note）----
    "两支安眠汇成一支：睡意浓成了催眠雾。": (
        "Two sleeps merge into one: the drowsiness thickens into hypnotic fog."),
    "两种寒液汇成一股：更冷的那种说了算。": (
        "Two cold liquids merge into one: the colder of the two decides."),
    "书页泡水：整片地板化开，淌成一汪纸浆。": (
        "Pages soak through: the whole floor dissolves and runs into a pool of paper pulp."),
    "亢奋压过麻意：麻药雾被咖啡因冲散。": (
        "Wakefulness overwhelms numbness: caffeine scatters the anesthetic fog."),
    "以太托住月光：轻的被点亮，凝成更亮的星辉。": (
        "Aether holds the moonlight aloft: the lighter element kindles into a brighter starlight."),
    "低语沉进忘川：只剩下一层稀释的印象。": (
        "Whispers sink into Lethe: only a diluted impression remains."),
    "再滑的流体也滑不出彻底的静：被一并滞住。": (
        "Even the slickest fluid cannot slip past utter stillness: it too is held fast."),
    "冷风卷过黑烟：吹散成一片浮动的灰。": (
        "Cold wind sweeps the black smoke: it scatters into drifting ash."),
    "冻脆的棋盘：整格碎裂，落回普通地面。": (
        "A frozen-brittle checkerboard: whole squares shatter and fall back to ordinary ground."),
    "冻裂的石面：防火层崩开，地面退回普通模样。": (
        "Cracked stone surface: the fireproof layer splits, and the ground returns to its "
        "ordinary form."),
    "冻裂的糙面：凸起剥落，地面退回普通模样。": (
        "Cracked rough surface: the ridges flake off, and the ground returns to its ordinary form."),
    "吸饱睡意的纸浆：滤出一汪镇静溶液。": (
        "Sleep-soaked pulp: it filters out a pool of sedative solution."),
    "回声学会了低语：雾里的每个回音都开始呢喃。": (
        "The echo learns to whisper: every echo in the fog begins to murmur."),
    "回声撞进遮蔽：连回音都被吞得无声无息。": (
        "The echo strikes the shroud: even the echo is swallowed without a trace."),
    "回声被吸声层吞掉：孔隙失效，地面退回普通模样。": (
        "The echo is swallowed by the sound-absorbing layer: its pores fail, and the ground "
        "returns to its ordinary form."),
    "声浪缠上湿汽：断续的握手声在雾里反复回放。": (
        "Sound waves cling to the damp vapor: broken handshake tones loop through the fog."),
    "孢子吃掉了噩梦：连恐惧都被抹成空白。": (
        "Spores eat the nightmare: even fear is wiped blank."),
    "孢子落进混沌：连混沌都被抹成一汪无念。": (
        "Spores fall into chaos: even chaos is blotted into a pool of no-thought."),
    "安抚：被镇住的泪水淡成了温热的稀释记忆。": (
        "Soothing: the stilled tears thin into warm diluted memory."),
    "寒液冻住水汽：霜意凝成一团清冷的晨雾。": (
        "Cold liquid freezes the vapor: the frost condenses into a cool morning mist."),
    "寒液冻住醚气：霜意凝成清冷的晨雾。": (
        "Cold liquid freezes the ether gas: the frost condenses into a cool morning mist."),
    "寒液浇透灼热：烫意退尽，地面退回普通模样。": (
        "Cold liquid floods the scorching heat: the burn drains away, and the ground returns "
        "to its ordinary form."),
    "忘川冲淡门之泪：温热的记忆只剩一点余温。": (
        "Lethe dilutes the door tears: the warm memory is left with only a trace of heat."),
    "忘川水洗去悔恨：锚锈崩落，只剩一段普通的墙。": (
        "Lethe water washes away the regret: the anchor's rust crumbles off, leaving an "
        "ordinary stretch of wall."),
    "忘川水洗掉蜡衣：墙露出本来的面目。": (
        "Lethe water strips the wax coat: the wall reveals what it truly is."),
    "忘川洗墨：墨色沉底，字迹随水忘掉。": (
        "Lethe washes the ink: the ink settles, and the writing is forgotten with the water."),
    "按实际1:1消耗液体并将同量胞尘变为惰性载气；部分转化需要邻格容量。": (
        "Consumes liquid 1:1 and turns the same amount of cell dust into inert carrier gas; "
        "partial conversion needs capacity in a neighboring cell."),
    "时间在以太里更滑了：连凝固点都留不住它。": (
        "Time grows slicker in aether: even its freezing point cannot hold it."),
    "星辉落在汞镜上：折出一滩会流动的月光。": (
        "Starlight falls on the mercury mirror: it refracts into a pool of flowing moonlight."),
    "显像墨泼向遮蔽：藏起来的东西全都显了形，泛成一片墨雾。": (
        "Revealing ink splashes over the shroud: everything hidden takes shape, blooming into "
        "a sheet of ink mist."),
    "显影液冲洗褪色：淡去的轮廓重新显影，成了一汪稀释记忆。": (
        "Developer fluid washes the fading trace: the faded outlines develop again into a pool "
        "of diluted memory."),
    "显影液把墨定了影：更浓、更稠，几乎不再流动。": (
        "Developer fluid fixes the ink: it grows deeper, thicker, and almost stops flowing."),
    "显影液漫过空白：没画完的底子显出普通的地面。": (
        "Developer fluid spreads across the blank: the unfinished base reveals ordinary ground."),
    "树脂被烘出香气：绿色的胶化成一缕安眠的香。": (
        "The resin bakes out its fragrance: the green gel becomes a thread of sleep-scented air."),
    "梦水兑进睡意：温和的镇静溶液就成了。": (
        "Dream water folds into the drowsiness: a gentle sedative solution takes shape."),
    "死寂掐断拨号音：握手声、蜂鸣声，全都哑了。": (
        "Dead silence cuts the dial tone: handshake tones and buzzes all fall mute."),
    "毒与酸互相喂饱：一团连骨头都能蚀穿的瘴。": (
        "Poison and acid feed each other: a miasma that eats through even bone."),
    "水冲灰烬：灰墙塌成一摊，地面冲得干干净净。": (
        "Water flushes the ash: the ash wall collapses into a heap, and the ground is scoured clean."),
    "水汽冲淡了显影：药性褪成温和的稀释记忆。": (
        "Water vapor dilutes the development: the reagent fades into gentle diluted memory."),
    "水汽凝住粉尘：脑海里的形状落进液面，成了一汪稀释记忆。": (
        "Water vapor binds the dust: the shapes in the mind fall onto the surface and become "
        "a pool of diluted memory."),
    "水汽收拢墨雾：字迹淡淡的，凝出一层能导电的稀墨。": (
        "Water vapor gathers the ink mist: the writing fades, condensing into a conductive thin ink."),
    "水淋月壤：细尘板结，地面退回普通模样。": (
        "Water drenches the moon soil: the fine dust packs down, and the ground returns to "
        "its ordinary form."),
    "水淹压电层：短路烧毁，地板退回普通地面。": (
        "Water floods the piezo layer: it burns out in a short circuit, and the floor reverts "
        "to ordinary ground."),
    "水面贴上寒液：整格冻成打滑的冰面。": (
        "Cold liquid meets the water surface: the whole cell freezes into a slippery ice sheet."),
    "汞吞掉磁化的记忆：金属腥味归一，只剩一滩银。": (
        "Mercury swallows the magnetized memory: the metallic tang collapses into a single pool "
        "of silver."),
    "汞遇辐射：蒸出一层无声的毒气。": (
        "Mercury meets radiation: it gives off a silent layer of poison gas."),
    "汞面被超流体冻住：一层脆亮的银冰。": (
        "The mercury surface freezes under superfluid: a brittle, gleaming sheet of silver ice."),
    "泡沫裹住低语：散开时，化成一小汪泪水。": (
        "Foam wraps the whispers: as it spreads, it becomes a small pool of tears."),
    "洁净的脑脊液滤过噩梦：配成一剂可用的注射用梦水。": (
        "Clean cerebral fluid filters the nightmare into a usable dose of injectable dream water."),
    "流动的时间撞进彻底的静：也被一并冻住。": (
        "Flowing time strikes utter stillness: it too freezes solid."),
    "海绵吸饱了水：孔泡瘫掉，地面退回普通模样。": (
        "The sponge soaks up the water: its pores collapse, and the ground returns to its "
        "ordinary form."),
    "液体重新化开：每个回音都学着呢喃。": (
        "The liquid melts back open: every echo imitates the murmur."),
    "液态蜡遇冷当场凝固，立起一堵蜡化记忆墙。": (
        "Liquid wax sets at once in the cold, raising a wall of waxed memory."),
    "深渊吞掉噩梦：纤维沉入黑渊，连梦本身都被忘掉。": (
        "The abyss swallows the nightmare: the fibers sink into the black deep, and even the "
        "dream is forgotten."),
    "混沌流进静滞：一切都还没开始就停了。": (
        "Chaos flows into stasis: everything stops before it can begin."),
    "混沌被清水稀释：浓得化不开的初衷淡成了一碗忘川水。": (
        "Chaos is diluted by clear water: the once-unbreakable first intent thins into a bowl "
        "of Lethe water."),
    "清水冲开湿墨，字迹变淡，留下能导电的稀墨。": (
        "Clear water washes the wet ink: the writing fades, leaving a conductive thin ink."),
    "清水泡开装帧胶：散架的书页淌成一汪纸浆。": (
        "Clear water soaks the binding glue: the pages come apart and run into a pool of paper pulp."),
    "清水稀释黏液：电花沉进液里，成了能导电的记忆。": (
        "Clear water dilutes the slime: the electric spark sinks in, becoming conductive memory."),
    "清醒叠着亢奋：咖啡因把香气推得更烈。": (
        "Wakefulness layers onto alertness: caffeine drives the fragrance sharper."),
    "湿汽裹住烟：黑烟吸饱水分，沉成昏黄的灰。": (
        "Damp vapor wraps the smoke: the black smoke soaks up water and settles into a dim "
        "yellow-grey ash."),
    "湿汽裹住睡意：沉沉地压成一团麻醉的雾。": (
        "Damp vapor wraps the drowsiness: it presses down into a heavy mass of anesthetic fog."),
    "灰尘蒙住反光：亮面失色，地面退回普通模样。": (
        "Dust veils the reflection: the bright face goes dull, and the ground returns to its "
        "ordinary form."),
    "灰尘蒙住星图：星星一颗颗熄灭，地面退回普通模样。": (
        "Dust veils the star chart: the stars go out one by one, and the ground returns to "
        "its ordinary form."),
    "热汽把酒汽点到了临界：随时可能着起来的可燃气。": (
        "Hot steam pushes the alcohol vapor to its threshold: a gas ready to ignite at any moment."),
    "热汽熏软木料：层层塌陷，地面退回普通模样。": (
        "Hot steam softens the timber: layer by layer it caves in, and the ground returns to "
        "its ordinary form."),
    "热汽熨过软垫：蓬松塌实，地面退回普通模样。": (
        "Hot steam irons the soft cushion: the fluff collapses, and the ground returns to its "
        "ordinary form."),
    "热汽逼出亢奋：橙色的雾一沾就让人坐不住。": (
        "Hot steam forces out the alertness: the orange fog makes anyone who touches it restless."),
    "热汽钻进空鼓：鼓包胀碎，地面退回普通模样。": (
        "Hot steam seeps into the hollow: the bulge bursts, and the ground returns to its "
        "ordinary form."),
    "热汽闷软了纸墙：层层瘫倒，化成纸浆。": (
        "Hot steam steams the paper wall soft: layer by layer it slumps and becomes paper pulp."),
    "热蜡裹住尖叫：块状的红没有化开，只是更沉了。": (
        "Hot wax wraps the scream: the block of red does not melt, it only grows heavier."),
    "热金属淬上热汽：一声闷响，只剩一股黑烟。": (
        "Molten metal quenches in the hot steam: a muffled thud, and only black smoke is left."),
    "热金属淬进水里：当场硬化，立成一截坚硬聚合墙。": (
        "Molten metal quenches in the water: it hardens on the spot into a stretch of solid "
        "aggregate wall."),
    "热金属渗进墙体：每拍完整度 −20，耗液 1；液量至少 5，熔穿后留下一洼余浆。": (
        "Molten metal seeps into the wall: −20 integrity per tick, 1 liquid consumed; needs at "
        "least 5 liquid, and leaves a pool of residue once it melts through."),
    "玻璃被冻得发脆：每拍完整度 −4，一碰就碎。": (
        "The glass freezes brittle: −4 integrity per tick, and it shatters on contact."),
    "磁带冻得发脆：带基一碰就断。": (
        "The tape freezes brittle: the ribbon snaps at a touch."),
    "稀薄的记忆液也能被冻得结结实实。": (
        "Even thin memory fluid can be frozen solid."),
    "纸堆泡了水：整片塌软，淌成一汪纸浆。": (
        "The paper pile soaks through: the whole patch slumps and runs into a pool of paper pulp."),
    "纸墙冻得又脆又硬：每拍完整度 −4，一碰就碎。": (
        "The paper wall freezes hard and brittle: −4 integrity per tick, and it shatters on contact."),
    "纸墙泡进水里：化开成一汪纸浆。": (
        "The paper wall soaks through: it melts into a pool of paper pulp."),
    "纸尘拌进黑烟：书卷气没了，只剩昏黄的灰。": (
        "Paper dust mixes into the black smoke: the bookish scent is gone, leaving only dim "
        "yellow-grey ash."),
    "纸浆吸饱了油：一桶更易燃的浆。": (
        "The paper pulp soaks up the oil: a bucket of pulp that burns even more readily."),
    "细雾洗过噩梦：具体的内容被洗掉，只剩深处含混的低语。": (
        "Fine mist washes over the nightmare: the details are rinsed away, leaving only a "
        "blurred whisper from the depths."),
    "绒毯吸饱了水：绒毛塌陷，地面退回普通模样。": (
        "The velvet soaks up the water: the pile collapses, and the ground returns to its "
        "ordinary form."),
    "色块冻得发脆：一碰就碎。": (
        "The color blocks freeze brittle: they shatter at a touch."),
    "药水唤醒银盐：颗粒显出形状，成了一缸显像墨。": (
        "The solution wakes the silver salts: the grains take shape, becoming a vat of revealing ink."),
    "药水洗掉七彩：牛奶褪回一缸干净的显影液。": (
        "The solution washes out the colors: the milk fades back into a vat of clean developer fluid."),
    "蒸汽熨过冰面：冻层化回普通的地面。": (
        "Steam irons the ice sheet: the frozen layer melts back into ordinary ground."),
    "薄气被熏黑：亮意散尽，退回一团普通的湿汽。": (
        "The thin vapor is smoked black: its brightness drains away, and it reverts to "
        "ordinary damp vapor."),
    "虹光凝进汞面：银色卷起七彩，搅成一滩彩虹牛奶。": (
        "Iridescence condenses onto the mercury surface: the silver gathers the colors and "
        "churns them into a pool of rainbow milk."),
    "虹光沉进星辉：七彩褪尽，只留下会流动的月光。": (
        "Iridescence sinks into the starlight: the colors drain away, leaving only flowing moonlight."),
    "蜜沉入酒：甜意沉底，成了一杯更厚的蜜酿。": (
        "Honey sinks into the wine: the sweetness settles, becoming a thicker cup of honeybrew."),
    "蜜网捕住浮灰：甜浆裹灰，成了黏稠的蜜灰膏。": (
        "The honey web catches the drifting ash: the sweet syrup wraps the ash into a sticky "
        "honey-ash paste."),
    "蜡柱被冻得发脆：每拍完整度 −4，几下就碎。": (
        "The wax pillar freezes brittle: −4 integrity per tick, and it breaks within a few hits."),
    "蜡油同宗：熔蜡化进燃油，只添分量不改性子。": (
        "Wax and oil are kin: molten wax folds into the fuel oil, adding bulk but not changing "
        "its nature."),
    "血封进蜡里：一汪暗红的膏，仍带着灵视的余温。": (
        "Blood seals into the wax: a dark red salve that still holds the warmth of second sight."),
    "超临界流体剥掉金属层：底下只剩普通的聚合地面。": (
        "Supercritical fluid strips the metal layer: only ordinary aggregate ground remains beneath."),
    "超临界流体钻透绝热层：分层剥落，地面退回普通模样。": (
        "Supercritical fluid drills through the thermal barrier: layer by layer it flakes away, "
        "and the ground returns to its ordinary form."),
    "超流体冷意更甚：液态蜡同样当场凝固。": (
        "The superfluid runs even colder: liquid wax sets on the spot as well."),
    "超流体冻实胶液：金胶褪成缓缓流动的凝胶基液。": (
        "The superfluid freezes the gel: the golden gel fades into a slowly flowing gel base."),
    "超流体的冷意一样能封住水面。": (
        "The superfluid's cold seals the water surface just as well."),
    "辐射尘落进湿汽：析出一层呛人的毒。": (
        "Radiation dust falls into the damp vapor: a layer of acrid poison separates out."),
    "辐射里的低语变了味：每一句都成了噩梦。": (
        "The whispers in the radiation turn sour: every line becomes a nightmare."),
    "追光的液体追上星辉：光溢出来，成了会流动的月光。": (
        "The light-chasing liquid catches the starlight: the light spills over, becoming "
        "flowing moonlight."),
    "酒气混着安眠：一沾就睡的浓度。": (
        "Alcohol vapor mixes with sleep: a concentration that puts you under at a touch."),
    "酒气醉进水里：清水被酿成了酒。": (
        "The alcohol vapor soaks into the water: the clear water is brewed into wine."),
    "酒精化冰：冰面悄悄退回普通地面。": (
        "Alcohol dissolves the ice: the ice sheet quietly reverts to ordinary ground."),
    "酸咬住熔金：热与蚀性搅成更凶的蚀金浆。": (
        "Acid bites into molten gold: heat and caustic bite churn into a fiercer gilt-etching slurry."),
    "酸泼上盐晶：剧烈溶蚀，墙崩解成一蓬呛人的毒气。": (
        "Acid splashes onto the salt crystal: violent dissolution, and the wall crumbles into "
        "a puff of acrid poison gas."),
    "酸渗进普通墙体：每拍完整度 −15，耗液 1；液量至少 5，蚀穿后留下一洼酸。": (
        "Acid seeps into an ordinary wall: −15 integrity per tick, 1 liquid consumed; needs at "
        "least 5 liquid, and leaves a pool of acid once it eats through."),
    "酸雾常年舔着玻璃：每拍完整度 −3，最终蚀穿。": (
        "Acid mist licks at the glass year after year: −3 integrity per tick, until it finally "
        "eats through."),
    "醉意沉进忘川：连酒香都只剩下模糊印象。": (
        "Drunkenness sinks into Lethe: even the scent of wine fades to a blurred impression."),
    "醒意顶开睡意：雾被蒸发成一缕透亮的薄气。": (
        "Wakefulness pushes the drowsiness aside: the fog evaporates into a wisp of clear thin vapor."),
    "醚与蜡同宗：两样易燃的东西混成一桶更浑的燃油。": (
        "Ether and wax are kin: two flammable things mix into a murkier barrel of fuel oil."),
    "银白的净汽落满灰尘：再也遮不住什么，只剩昏沉的弥散。": (
        "The silver-white clean vapor settles full of dust: it can hide nothing now, only a "
        "dim diffusion remains."),
    "镜面被冻得发脆：黑镜上爬满裂痕。": (
        "The mirror surface freezes brittle: cracks crawl across the black mirror."),
    "雾沉进水里：刺痒的电流溶进清水，成了导电的液态记忆。": (
        "The fog sinks into the water: the prickling current dissolves into clear water, "
        "becoming conductive liquid memory."),
    "静电把燃油蒸到临界：一蓬随时能着的气。": (
        "Static charge pushes the fuel oil to its threshold: a plume of gas ready to ignite "
        "at any moment."),
    "静电擦过可燃气：没燃成明火，只腾起灼热的汽。": (
        "Static charge grazes the flammable gas: no open flame, only a surge of scalding vapor."),
    "静电擦过醚气：淡紫的雾腾起一阵灼热。": (
        "Static charge grazes the ether gas: the pale violet mist throws off a burst of heat."),
    "静电溶进清水：水从此带了电。": (
        "Static charge dissolves into the clear water: the water now carries a current."),
    "静电落进导电液：整片液面离子化，腾起电浆雾。": (
        "Static charge falls into the conductive liquid: the whole surface ionizes, raising "
        "a plasma mist."),
    "麻醉溶进清水：成了一剂温和的镇静溶液。": (
        "The anesthetic dissolves into the clear water: a gentle sedative solution."),
}
