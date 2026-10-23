"""环境和征兆的玩家文案；不参与数值结算。"""

WALL_PROSE = {
    '理念立方体': ('纯白的立方体，棱角没有一丝磨损。推得动，砸不坏。', 'A pure white cube with unworn edges. It can be pushed, but not broken.'),
    '合辙枢': ('两股电流在枢心汇合，才有火花沿另一端奔出。同一回合须收到至少两个不同来源的信号。', 'Two currents meet at its heart before a spark leaves the other end. It needs signals from at least two different sources in the same round.'),
    '分流枢': ('收到一丝电流，四周接线便一齐亮起。任何信号都以满强度传出。', 'A trace of current lights its surrounding wires. Any incoming signal is passed on at full strength.'),
    '接线枢': ('四根线在盒中接成十字，电流穿过时没有减弱。', 'Four wires form a cross inside the box. Current passes through without weakening.'),
    '陷阱石台': ('看起来只是普通石台，台面下却藏着机关。取走物品或回应台上事件时，机关随即发动。', 'It looks like an ordinary plinth, but a mechanism hides beneath it. Taking its item or answering its event sets it off.'),
    '机关石台': ('石台下藏着机关。取走台上物品或回应事件，会让门扉开启、灯光亮起，或使附近地形显影。', 'A mechanism hides beneath the plinth. Taking its item or answering its event may open a door, light a lamp, or develop nearby terrain.'),
    '机关门': ('门轴连着暗处的线。每收到一次信号，门便在开与关之间切换；门板比普通门略有色差。', 'Wires lead from its hinges into the dark. Each signal toggles it open or shut; its color differs slightly from an ordinary door.'),
    '显影方尖': ('暗着的尖碑等待电流。收到信号便亮起，周围地形从此留在视野的记忆中。', 'The dark obelisk waits for a current. A signal lights it and permanently develops the surrounding terrain.'),
    '清醒石': ('石面透着凉意。相邻格不分敌我，醉意、麻痹、迟钝、深眠、遮蔽、安眠与褪黑素征兆都无法停留。', 'Coolness seeps from its surface. On adjacent cells, friend and foe alike cannot keep drunkenness, paralysis, sluggishness, deep sleep, obscurity, sleepiness, or melatonin portents.'),
    '梦晶簇': ('晶尖里积着一团雾，仍在吸入周围九格的气体。只容一种，最多一百单位；晶簇破碎，封存的雾便尽数涌出。', 'Mist gathers inside its points as it draws gas from the surrounding 3×3 cells. It holds one kind, up to 100 units; breaking it releases all the stored gas.'),
    '木桌子': ('梦游者留下的木桌，桌面托着物品与未完的事情。桌身占住一格，无法穿行；站在邻格可以取物或回应台上的事件。', 'A sleepwalker left this table, bearing items and unfinished affairs. It occupies one impassable cell; items and events can be reached from an adjacent cell.'),
    '石台': ('厚重的石座把物品和未完的事情托在面前。台身占住一格，无法穿行；站在邻格可以取物或回应台上的事件。', 'A heavy stone plinth holds items and unfinished affairs before you. It occupies one impassable cell; items and events can be reached from an adjacent cell.'),
    '赤致密聚合墙': ('赤色的墙沉沉压在眼前，比浅梦的墙更密、更硬。', 'A red wall weighs upon the eye, denser and harder than the walls of shallow dreams.'),
    '黄致密聚合墙': ('厚重的黄墙，像许多年压成的一块旧纸。', 'A heavy yellow wall, like years pressed into a slab of old paper.'),
    '蓝致密聚合墙': ('蓝色密墙冰冷，贴近时连呼吸也像结了霜。', 'The dense blue wall is cold; even your breath seems to frost beside it.'),
    '绿致密聚合墙': ('绿墙厚得听不见另一边的声音。', 'The green wall is too thick to hear anything beyond it.'),
    '无意识结晶': ('深处的雾凝成晶体，又继续吸入周围九格的气体。最多封存一百六十单位，打碎便全部放出。', 'Deep mist has crystallized, drawing more gas from the surrounding 3×3 cells. It stores up to 160 units and releases them all when broken.'),
    '石墨烯晶格': ('六边形一层扣着一层，硬韧得难以破开，却能一格格推动。', 'Layers of hexagons lock together, too hard and tough to break easily, yet movable one cell at a time.'),
    '压电地板': ('脚底渐渐传来电流。站在其上每回合蓄一层电，离开后每回合散去一层。积满四层便向周围九格放电，造成两点清醒创伤，随后变回普通地面；你也会受伤，稳定意识不受伤。', 'Current builds beneath your feet: one charge per round while occupied, one lost per round after you leave. Four charges discharge across the surrounding 3×3 cells for 2 lucidity trauma, then the tile becomes ordinary floor. You can be hurt; stable consciousnesses cannot.'),
    '推书车': ('书页塞满木车，推过时纸角簌簌作响。可以推动，挡住直线通路，也会燃烧。', 'Pages fill the wooden cart, rustling as it moves. It can be pushed, obstructs straight paths, and can burn.'),
    '黄铜阅读灯': ('黄铜灯罩把光拢在周围三格，谁走近都能借光看远。灯体可以打碎。', 'The brass shade casts light across three cells. Anyone nearby can see farther by it. The lamp can be broken.'),
    '嵌壁梦灯': ('灯罩里透出一口暖息，把周围两格照出淡米色。站在邻格可以开或关；灯体不结实，砸碎就彻底暗下去。', 'A warm breath of light shows through the shade, tinting the two surrounding cells pale beige. It can be switched from an adjacent cell, and its body is fragile: smash it and the niche goes dark for good.'),
    '弧光灯架': ('冷白的光从金属网里漏出来，混着一点臭氧味。它只跟电路走：那段线通电才亮，一断电立刻熄，砸碎也不会替你供电。', 'Cold white light leaks through the metal mesh with a tang of ozone. It follows the circuit alone: it lights only while that line is energized, dies the moment power is cut, and smashing it gives you no power.'),
    '余烬灯盏': ('灯盏里压着没烧尽的余烬，点着以后能照亮周围两格。它照常烧穿自己：火一熄就暗下来，水浇过也一样。', 'Unburnt embers sit in the lamp; once lit it lights the two cells around it. It burns through itself as any fuel would — the light dies when the flame does, water included.'),
}

LIQUID_PROSE = {
    '电解黏液': ('细小电花在金黄黏液中闪动。蹚过时脚步变慢，电流也会沿它传来。', 'Tiny sparks flash in golden slime. Wading through slows your steps and lets current travel through it.'),
    '液化的回声': ('一句话折了又折，化成液体。蹚过去，自己的声响便传得两倍远。', 'A sentence folded over and over has become liquid. Wading through doubles the radius of your sounds.'),
    '记忆泡沫': ('浅色泡沫软软裹住身体，替下一次创伤挡去两点，随即散开。', 'Pale foam softly wraps the body, absorbing 2 points of the next trauma before dispersing.'),
    '磁化液态记忆': ('深蓝液面带着金属腥味。站在里面，会被缓缓牵向最近的金属固体。', 'The deep blue liquid smells of metal. Standing in it slowly draws you toward the nearest metal solid.'),
    '显像墨': ('墨绿浓液漫过脚面。接下来六回合，视野里的异象连伪装也藏不住。', 'Dark green ink covers your feet. For six rounds, anomalies in sight cannot hide even behind disguises.'),
    '凝固的尖叫': ('暗红的块状液体贴上身体，心智渐渐流失，感官却愈发敏锐。', 'Dark red clots cling to your body, draining mind while sharpening your senses.'),
    '门之泪': ('圣所门槛渗出的泪还带着温度。蹚过后，每四回合恢复一点想象力。', 'Tears seeping from the sanctuary threshold are still warm. After wading through, you recover 1 imagination every four rounds.'),
    '水银': ('水银沉沉压着脚面，也让同格的毒气更容易侵入身体。气体生效所需的浓度降低了。', 'Mercury weighs on your feet and makes gas on the same cell easier to breathe in. Less gas is needed for its effect to take hold.'),
    '超临界流体': ('液流自己钻进邻墙的缝隙，一点点剥蚀墙身，坚硬的聚合墙也留不住它。', 'The fluid seeps into neighboring walls on its own, eating them away; even hard polymer walls cannot keep it out.'),
    '液氦': ('银色液流逆着高低地势铺开，经过的火焰立即熄灭，身上也不留下征兆。', 'Silver liquid spreads regardless of elevation, extinguishing fire as it passes and leaving no portent on the body.'),
}

GAS_PROSE = {
    '消兆薄雾': ('浅青的细雾里，远处仍看得清。普通地面上，每三回合散去一单位。', 'You can still see through the pale cyan mist. On ordinary floor, one unit disperses every three rounds.'),
    '梦醚气': ('淡紫气团使远处略显模糊，碰上火便会燃烧。普通地面上，每三回合散去一单位。', 'Pale violet gas slightly blurs distant sights and burns on contact with fire. On ordinary floor, one unit disperses every three rounds.'),
    '醒素薄气': ('浅蓝薄气透着亮意，视线穿过它没有受阻。普通地面上，每三回合散去一单位。', 'Light shines through the pale blue gas without obstructing sight. On ordinary floor, one unit disperses every three rounds.'),
    '无垢蒸汽': ('银白蒸汽轻得遮不住眼前的东西。普通地面上，每三回合散去一单位。', 'The silver steam is too light to obscure what lies ahead. On ordinary floor, one unit disperses every three rounds.'),
    '胞尘': ('浅绿的小粒浮在空中，慢慢聚成气团。普通地面上，每四回合散去一单位。', 'Pale green particles slowly gather into clouds. On ordinary floor, one unit disperses every four rounds.'),
    '无菌载气': ('淡蓝气团静静飘着，吸入也不会使身体免疫。普通地面上，每四回合散去一单位。', 'Pale blue gas drifts quietly; breathing it grants no immunity. On ordinary floor, one unit disperses every four rounds.'),
}

PLANT_PROSE = {
    '捕梦草': ('叶片在脚落下时卷合，缠住你的腿，让下一回合无法移动。', 'Its leaves curl around your legs when stepped on, preventing movement next round.'),
    '荆棘藤': ('高高的棘藤遮住视线，穿过时留下划痕，造成一点清醒创伤。', 'Tall thorny vines block sight. Passing through scratches you for 1 lucidity trauma.'),
    '融蜡花': ('蜡质花瓣透着暖黄光。拔下时花身融开，留下一件熔融蜡烛液体弹。', 'Wax petals glow warm yellow. Pulling it up melts the flower into one molten-candle liquid projectile.'),
    '贤者之苔': ('金黄的苔绒贴着地面。拔下可得贤者之粉，恢复十五点想象力，却让清醒缓慢流失。', 'Golden moss clings to the ground. Harvesting yields sage powder, restoring 15 imagination while slowly draining lucidity.'),
    '千梦铃兰': ('细茎挂满小铃。贴近时心头清朗，免疫控制类征兆；拔下铃铛摇响，可以拖慢周围的失控意识。', 'Tiny bells cover its stems. Nearby, clarity grants immunity to control portents; a harvested bell can be rung to slow nearby uncontrolled consciousnesses.'),
    '彩玻菌': ('彩色菌盖像玻璃，夜里自己发光，不易燃烧。拔下可得彩玻碎片；踩碎时清脆一响，散出少量呢喃。', 'Its colored glasslike cap glows at night and is hard to ignite. Harvesting yields colored glass shards; crushing it rings out and releases a little whispering gas.'),
}

PORTENT_PROSE = {
    'calmed': ('惊惶被压住，毒气、腐蚀、燃烧和下潜反噬不再侵蚀心智；异象仍能伤到你。', 'Panic subsides. Gas, corrosion, fire, and diving backlash no longer drain mind; anomalies can still hurt you.'),
    'burning': ('余火仍在身上烧：离开火焰后，每两回合失去一点清醒。留在火中只承受直接灼伤，入水便熄灭。', 'Embers still burn on you: after leaving fire, lose 1 lucidity every two rounds. In fire, only direct burns apply; water extinguishes them.'),
    'cursed_sight': ('所有失控意识的位置与形态都向你敞开，伪装也不例外。它们同样看见你，你的声音还会传得两倍远。', 'Every uncontrolled consciousness reveals its position and form, even through disguise. They see you in return, and your sounds travel twice as far.'),
    'honeyed': ('蜂蜜护着伤口，每两回合恢复清醒；越往深处越多，从一点增至三点，每层最多恢复六点。沾蜜的生物移动慢一半。', 'Honey protects wounds, restoring lucidity every two rounds: 1 to 3 points with depth, at most 6 per layer. Honey-covered creatures move at half speed.'),
    'clarity': ('香气驱散迷醉，醉意、麻痹、迟钝、深眠、安眠和褪黑都无法沾身。', 'The scent clears your head, warding off drunkenness, paralysis, sluggishness, deep sleep, sleepiness, and melatonin.'),
    'invigorated': ('薄荷的凉意还在，每两回合恢复清醒；越往深处越多，从一点增至三点。', 'Mint coolness lingers, restoring lucidity every two rounds: 1 to 3 points with depth.'),
    'nightmare': ('梦的边缘在啃食意识。每两回合失去心智，越往深处越重，从一点增至三点。', 'The edges of the dream gnaw at consciousness. Every two rounds, lose 1 to 3 mind with increasing depth.'),
    '呛尘': ('档案里的陈灰呛进肺里，视野少一格。每三回合失去清醒，越往深处越重，从一点增至三点。', 'Old archive dust chokes your lungs, reducing vision by one cell. Every three rounds, lose 1 to 3 lucidity with increasing depth.'),
    'sk_faded_ink': ('批注褪色，想象力也跟着消失：每回合少一点，持续两回合，深处也不会加重。', 'As annotations fade, imagination fades with them: lose 1 each round for two rounds, without depth scaling.'),
    'sk_rooted': ('句子停在脚下，下一回合无法移动；仍可使用道具、展开构想或攻击。', 'The sentence stops beneath your feet. You cannot move next round, but can still use items, unfold ideas, or attack.'),
    'sk_field_hamper': ('周围的介质缠住脚步，每步多花零点二回合。', 'The surrounding medium catches your feet, adding 0.2 rounds to each step.'),
    'hospital_diagnosed': ('诊断的痕迹暂时留着，视线里的伪装因而能被识破。', 'A trace of the diagnosis lingers, exposing disguises within ordinary sight.'),
    'hospital_ether_liquid': ('梦醚拖慢脚步，每步多花零点一五回合；与梦醚气相遇，只取较慢的一份。', 'Ether slows your steps by 0.15 rounds each. With ether gas, only the larger delay applies.'),
    'hospital_ether_gas': ('吸入的梦醚拖慢脚步，每步多花零点一五回合；与梦醚液相遇，只取较慢的一份。', 'Breathed ether slows your steps by 0.15 rounds each. With ether liquid, only the larger delay applies.'),
    'hospital_spore': ('胞尘附在身上，每五回合造成一点心智创伤；更多同类胞尘不会加重这份创伤。', 'Spores cling to you, causing 1 mind trauma every five rounds. More of the same spores do not increase it.'),
    'hospital_awake': ('眼前亮了一点，视野多出一格，行动仍照常耗时。', 'The view brightens, extending vision by one cell. Actions still take their usual time.'),
    'hospital_silver': ('银盐的微光暂时照出视线里的隐匿者，照不到视野之外。', 'Silver-salt glimmers briefly reveal hidden beings in sight, but cannot reach beyond it.'),
    'hospital_steam': ('薄薄的水汽沾在身上，使你湿润，清醒、心智与想象力并未因此恢复。', 'A film of steam leaves you wet, without restoring lucidity, mind, or imagination.'),
    'hospital_lymph_hit': ('药效等待下一次直接命中病原体，添上两点创伤，然后消退。', 'The medicine waits for your next direct hit on a pathogen, adds 2 trauma, then fades.'),
    'hospital_immune_once': ('药片替你缩短下一项新沾染的负面征兆：少两回合，仍至少留一回合。', 'The tablet shortens the next newly acquired negative portent by two rounds, leaving at least one.'),
    'hospital_pain_buffer': ('糖衣垫住第一次心智创伤，替你挡去两点；清醒创伤仍会照常到来。', 'The sugar coating absorbs 2 points of the first mind trauma. Lucidity trauma still arrives unchanged.'),
}

EN_ENVIRONMENT_PROSE = {
    zh: en for table in (WALL_PROSE, LIQUID_PROSE, GAS_PROSE, PLANT_PROSE, PORTENT_PROSE)
    for zh, en in table.values()
}

ANOMALY_NOTE_PROSE = {
    ('anomaly.disco_echo', 'passive'): (
        '频闪｜转动的球灯晃得人眼花。在它视野内，你的视野减半。',
        'Strobe | The turning mirror ball dazzles you. Within its sight, your vision is halved.'),
    ('anomaly.cursor_hunter', 'passive'): (
        '指针锁定｜一旦开始追踪，箭头便直奔目标，移动耗时减半。',
        'Cursor lock | Once tracking begins, the arrow heads straight for its target, halving its movement time.'),
    ('anomaly.core_y2k_worm', 'skill'): (
        '孵化请求、进程繁殖、系统迁移｜完整度越低，它越急着孵出千禧园的低阶异象来护卫自己。三个阶段都能召唤；最后一段还会瞬移，离开战场。',
        'Hatch Request, Process Breeding, System Migration | As its integrity falls, it hastens to hatch lesser Millennium Garden anomalies as guards. It can summon in all three phases; in the last, it also teleports away from combat.'),
}
EN_ENVIRONMENT_PROSE.update({zh: en for zh, en in ANOMALY_NOTE_PROSE.values()})
